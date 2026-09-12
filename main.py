import asyncio
import logging
import socket
import threading
import time
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from starlette.exceptions import HTTPException as StarletteHTTPException

import app.db_models  # noqa: F401 - registers SQLAlchemy models before create_all
from app.api import router as api_router
from app.core import settings
from app.database import Base, SessionLocal, engine
from app.db_models import Position, SignalLog, TradeHistory
from app.web import router as web_router
from app.ws import broadcast_closed_trades, manager as ws_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

try:
    Base.metadata.create_all(bind=engine)
except Exception:
    logger.exception("Database initialization failed; the dashboard will run in degraded mode.")

app = FastAPI(title="Forex Trading Bot", version="3.0.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(api_router)
app.include_router(web_router)


@app.exception_handler(StarletteHTTPException)
async def themed_404_handler(request: Request, exc: StarletteHTTPException):
    """Browser navigation gets the site-themed 404 page; API callers keep plain JSON."""
    if exc.status_code == 404 and "text/html" in request.headers.get("accept", ""):
        from app.web import templates
        return templates.TemplateResponse(request, "404.html", {"active_page": ""}, status_code=404)
    return await http_exception_handler(request, exc)

SIGNAL_ENGINE_INTERVAL_SECONDS = 15 * 60


async def _signal_engine_loop() -> None:
    """Run the RSI signal engine on a timer for as long as the app is up.

    This is what makes the bot 'autonomous' rather than purely reactive: it
    doesn't wait for an external caller, it checks the market itself. An
    equivalent n8n Schedule -> HTTP Request workflow (see n8n_workflows/) can
    trigger the same POST /signals/run-now endpoint instead or in addition.
    """
    from app.signal_engine import run_once

    while True:
        try:
            db = SessionLocal()
            try:
                results = await asyncio.to_thread(run_once, db)
                fired = [r for r in results if r.get("action")]
                if fired:
                    logger.info("Signal engine produced %d signal(s): %s", len(fired), fired)
                for r in results:
                    if r.get("positions_closed"):
                        await broadcast_closed_trades(db, r["symbol"], r["positions_closed"])
            finally:
                db.close()
        except Exception:
            logger.exception("Signal engine loop failed; will retry next interval.")
        await asyncio.sleep(SIGNAL_ENGINE_INTERVAL_SECONDS)


LIVE_TICK_SECONDS = 5
RSI_REFRESH_EVERY_N_TICKS = 12  # ~60s, keeps the free FX API call rate low


async def _live_broadcast_loop() -> None:
    """Push a lightweight snapshot to every connected dashboard every few seconds.

    RSI needs a real (rate-limited) market data fetch, so it's only recomputed
    every RSI_REFRESH_EVERY_N_TICKS ticks; DB counts are cheap and refresh every tick.
    """
    from app.signal_engine import preview_signals

    tick = 0
    cached_rsi: list[dict] = []
    while True:
        try:
            if not ws_manager.active:
                tick += 1
                await asyncio.sleep(LIVE_TICK_SECONDS)
                continue

            if tick % RSI_REFRESH_EVERY_N_TICKS == 0:
                cached_rsi = await asyncio.to_thread(preview_signals)

            db = SessionLocal()
            try:
                open_positions = db.query(Position).filter(Position.status == "OPEN").count()
                signals_today = db.query(func.count(SignalLog.id)).scalar() or 0
                recent = (
                    db.query(SignalLog).order_by(SignalLog.created_at.desc()).limit(8).all()
                )
                recent_signals = [
                    {
                        "symbol": s.symbol,
                        "action": s.action,
                        "source": s.signal_source,
                        "confidence": float(s.confidence_score) if s.confidence_score is not None else None,
                    }
                    for s in recent
                ]
                closed = (
                    db.query(TradeHistory).order_by(TradeHistory.closed_at.desc()).limit(8).all()
                )
                closed_trades = [
                    {
                        "symbol": t.symbol,
                        "exit_price": float(t.exit_price),
                        "profit_loss": float(t.profit_loss),
                        "closed_at": t.closed_at.strftime("%d %b %H:%M") if t.closed_at else "-",
                    }
                    for t in closed
                ]
            finally:
                db.close()

            await ws_manager.broadcast({
                "type": "tick",
                "open_positions": open_positions,
                "signals_today": signals_today,
                "rsi_readings": cached_rsi,
                "recent_signals": recent_signals,
                "closed_trades": closed_trades,
                "server_time": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            logger.exception("Live broadcast loop failed; will retry next tick.")
        tick += 1
        await asyncio.sleep(LIVE_TICK_SECONDS)


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.on_event("startup")
async def start_signal_engine() -> None:
    asyncio.create_task(_signal_engine_loop())
    asyncio.create_task(_live_broadcast_loop())


PORT = 9999


def _open_browser_when_ready(port: int, timeout: float = 30.0) -> None:
    """Poll localhost:port until the server accepts connections, then open it.

    Runs once per `python main.py` invocation (not per --reload restart), since
    it lives in the reloader process, not the worker uvicorn re-spawns on
    every file change.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                webbrowser.open(f"http://localhost:{port}")
                return
        except OSError:
            time.sleep(0.3)


if __name__ == "__main__":
    threading.Thread(target=_open_browser_when_ready, args=(PORT,), daemon=True).start()
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
