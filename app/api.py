import asyncio
import logging
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import settings
from app.database import get_db
from app.db_models import NewsPost, Position, SignalLog, TradeHistory
from app.models import ChatRequest, NewsDraftRequest, NewsPublishRequest, QuoteUpdate, TradeSignal
from app.paper import apply_paper_quote, create_paper_metadata
from app.risk import validate_signal_risk
from app.services import execute_order, get_demo_open_position_count
from app.sizing import STARTING_BALANCE, size_position
from app.ws import broadcast_closed_trades, manager as ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "trading_mode": settings.trading_mode}


def process_signal(signal: TradeSignal, db: Session) -> dict:
    """Shared pipeline: log → risk-check → execute → persist.

    Used by both the public /webhook/signal endpoint and the internal RSI
    signal engine, so every entry point goes through the exact same risk
    rules and execution path.
    """
    db.add(SignalLog(symbol=signal.symbol, signal_source=signal.source, action=signal.action,
                     confidence_score=signal.confidence_score))
    db.commit()

    try:
        live_open_position_count = (
            get_demo_open_position_count(signal.symbol)
            if settings.trading_mode == "DEMO" else None
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    decision = validate_signal_risk(signal, db, live_open_position_count)
    if not decision.allowed:
        logger.warning("Rejected signal %s %s: %s", signal.action, signal.symbol, decision.reason)
        return {"status": "rejected", "message": decision.reason}

    result = execute_order(signal)
    if result.get("status") in {"PAPER_FILLED", "FILLED"}:
        position = Position(symbol=signal.symbol, order_type=signal.action, volume=signal.volume,
                            entry_price=result["price"], status="OPEN")
        db.add(position)
        db.commit()
        db.refresh(position)
        if result.get("status") == "PAPER_FILLED":
            create_paper_metadata(db, position, signal.stop_loss, signal.take_profit)
            db.commit()
    if result.get("status") in {"error", "failed", "rejected"}:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "success", "message": "Order processed", "details": result}


@router.post("/webhook/signal")
def receive_signal(signal: TradeSignal, db: Session = Depends(get_db)):
    return process_signal(signal, db)


@router.post("/paper/quote")
def update_paper_quote(quote: QuoteUpdate, db: Session = Depends(get_db)):
    if settings.trading_mode != "PAPER":
        raise HTTPException(status_code=409, detail="Paper quote updates require PAPER mode.")
    closed = apply_paper_quote(db, quote.symbol, quote.price)
    return {"status": "ok", "symbol": quote.symbol, "price": quote.price, "closed_positions": closed}


@router.post("/news/publish")
def publish_approved_news(news: NewsPublishRequest, db: Session = Depends(get_db)):
    """Legacy one-shot endpoint: creates a post that is immediately PUBLISHED.

    Kept for manual testing / backward compatibility. The n8n news pipeline now
    uses the draft -> approve flow below instead, so a generated image and a
    short numeric approval id can travel with the post.
    """
    post = NewsPost(
        title=news.title,
        summary=news.summary,
        source_url=news.source_url,
        instagram_caption=news.instagram_caption,
        image_url=news.image_url,
        status="PUBLISHED",
        approved_at=datetime.now(timezone.utc),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"status": "published", "post_id": post.id, "instagram_status": "DRAFT_READY"}


@router.post("/news/draft")
def create_news_draft(news: NewsDraftRequest, db: Session = Depends(get_db)):
    """Called by the n8n news-analysis workflow right after the AI + image step.

    Stores the AI analysis and the generated image URL as a DRAFT (not shown
    on the public /news page yet) and returns a short numeric id. A human
    approves it later in Telegram with `/paylas <id>` -- no retyping needed.
    """
    post = NewsPost(
        title=news.title,
        summary=news.summary,
        source_url=news.source_url,
        instagram_caption=news.instagram_caption,
        image_url=news.image_url,
        status="DRAFT",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"status": "draft", "id": post.id}


@router.post("/news/{post_id}/approve")
def approve_news_draft(post_id: int, db: Session = Depends(get_db)):
    """Called by the n8n approval workflow when an admin sends /paylas <id>."""
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail=f"No draft with id {post_id}")
    if post.status == "PUBLISHED":
        return {"status": "already_published", "id": post.id}
    post.status = "PUBLISHED"
    post.approved_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "published", "id": post.id, "instagram_status": "DRAFT_READY"}


@router.post("/news/{post_id}/reject")
def reject_news_draft(post_id: int, db: Session = Depends(get_db)):
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail=f"No draft with id {post_id}")
    post.status = "REJECTED"
    db.commit()
    return {"status": "rejected", "id": post.id}


@router.get("/news/posts")
def list_published_news(db: Session = Depends(get_db)):
    posts = (
        db.query(NewsPost)
        .filter(NewsPost.status == "PUBLISHED")
        .order_by(NewsPost.approved_at.desc())
        .limit(20)
        .all()
    )
    return [
        {"id": post.id, "title": post.title, "summary": post.summary,
         "source_url": post.source_url, "instagram_caption": post.instagram_caption,
         "image_url": post.image_url, "published_at": post.approved_at}
        for post in posts
    ]


@router.get("/market/history/{symbol}")
def market_history(symbol: str):
    """Daily close price series for one allowed FX pair, used to draw the price chart."""
    symbol = symbol.upper().strip()
    if symbol not in settings.allowed_symbols:
        raise HTTPException(status_code=404, detail=f"Symbol not tracked: {symbol}")
    from app.market_data import fetch_daily_series
    return {"symbol": symbol, "points": fetch_daily_series(symbol)}


@router.get("/signals/preview")
def preview_signals():
    """Read-only RSI snapshot for every allowed symbol. No orders are placed."""
    from app.signal_engine import preview_signals as _preview
    return {"readings": _preview()}


@router.post("/signals/run-now")
async def run_signal_engine(db: Session = Depends(get_db)):
    """Compute RSI for every allowed symbol and submit real signals where triggered.

    Called automatically every 15 minutes by the background task in main.py,
    and on demand by the dashboard's 'Siqnalı indi yarat' button / an n8n
    Schedule -> HTTP Request workflow.
    """
    from app.signal_engine import run_once
    results = run_once(db)
    for r in results:
        if r.get("positions_closed"):
            await broadcast_closed_trades(db, r["symbol"], r["positions_closed"])
    return {"results": results}


@router.get("/equity/history")
def equity_history(db: Session = Depends(get_db)):
    """Cumulative PAPER equity curve built from closed trades only (never fabricated)."""
    trades = db.query(TradeHistory).order_by(TradeHistory.closed_at.asc()).all()
    balance = STARTING_BALANCE
    points = [{"t": None, "balance": round(balance, 2)}]
    for trade in trades:
        balance += float(trade.profit_loss)
        points.append({
            "t": trade.closed_at.isoformat() if trade.closed_at else None,
            "balance": round(balance, 2),
        })
    return {
        "starting_balance": STARTING_BALANCE,
        "current_balance": round(balance, 2),
        "trade_count": len(trades),
        "points": points,
    }


@router.get("/market/analysis")
def market_analysis():
    from app import assistant
    return {"analysis": assistant.analyze_market()}


@router.post("/chat")
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    from app import assistant
    reply = assistant.ask(db, payload.message, [item.model_dump() for item in payload.history])
    return {"reply": reply}


# Fixed, plausible reference prices so the presentation demo never depends on an
# external FX API being reachable -- the signal that fires still goes through the
# exact same TradeSignal -> risk -> execution pipeline as every other entry point.
DEMO_REFERENCE_PRICES = {"EURUSD": 1.0850, "GBPUSD": 1.2650, "USDJPY": 158.20}


@router.post("/demo/run")
async def run_live_demo(db: Session = Depends(get_db)):
    """Fires one real, risk-checked PAPER signal for the live presentation demo."""
    candidates = [s for s in settings.allowed_symbols if s in DEMO_REFERENCE_PRICES] or list(DEMO_REFERENCE_PRICES)
    # Prefer a symbol that isn't already at the open-position limit, so the demo
    # succeeds more often than not; if every candidate is full, fall back to a
    # random one anyway -- a live risk rejection is a legitimate demo moment too.
    open_counts = {
        symbol: db.query(Position).filter(Position.symbol == symbol, Position.status == "OPEN").count()
        for symbol in candidates
    }
    eligible = [s for s in candidates if open_counts[s] < settings.max_open_positions_per_symbol]
    symbol = random.choice(eligible or candidates)
    price = DEMO_REFERENCE_PRICES[symbol]
    action = random.choice(["BUY", "SELL"])

    from app.sizing import STOP_PIPS, TARGET_PIPS, pip_size
    size = pip_size(symbol)
    stop_buffer, target_buffer = STOP_PIPS * size, TARGET_PIPS * size
    if action == "BUY":
        stop_loss = round(price - stop_buffer, 5)
        take_profit = round(price + target_buffer, 5)
    else:
        stop_loss = round(price + stop_buffer, 5)
        take_profit = round(price - target_buffer, 5)

    volume = size_position(db, symbol)
    signal = TradeSignal(
        symbol=symbol, action=action, volume=volume, source="LIVE_DEMO",
        entry_price=price, stop_loss=stop_loss, take_profit=take_profit, confidence_score=88.0,
    )
    result = process_signal(signal, db)

    payload = {
        "type": "signal_fired",
        "symbol": symbol,
        "action": action,
        "entry_price": price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "volume": volume,
        "status": result.get("status"),
    }
    await ws_manager.broadcast(payload)

    # If the position actually opened, simulate the market reaching take_profit a
    # beat later so the equity curve visibly moves during the same demo click.
    closed_profit_loss = None
    if result.get("status") == "success":
        opened = (
            db.query(Position)
            .filter(Position.symbol == symbol, Position.status == "OPEN")
            .order_by(Position.created_at.desc())
            .first()
        )
        await asyncio.sleep(1.4)
        if opened is not None:
            apply_paper_quote(db, symbol, take_profit)
            trade = (
                db.query(TradeHistory)
                .filter(TradeHistory.position_id == opened.id)
                .order_by(TradeHistory.closed_at.desc())
                .first()
            )
            if trade is not None:
                closed_profit_loss = float(trade.profit_loss)
                await ws_manager.broadcast({
                    "type": "trade_closed", "symbol": symbol, "profit_loss": closed_profit_loss,
                })

    payload["closed_profit_loss"] = closed_profit_loss
    return payload
