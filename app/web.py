from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import settings
from app.database import get_db
from app.db_models import NewsPost, Position, SignalLog, TradeHistory
from app.sizing import current_balance

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


def _as_float(value: Decimal | float | int | None) -> float:
    return float(value) if value is not None else 0.0


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    database_error = None
    session: Session | None = None
    context = {
        "open_positions": 0,
        "signals_today": 0,
        "recent_signals": [],
        "positions": [],
        "closed_trades": [],
        "current_balance": 10_000.0,
    }
    try:
        session = next(get_db())
        context["open_positions"] = session.query(Position).filter(Position.status == "OPEN").count()
        context["signals_today"] = session.query(func.count(SignalLog.id)).scalar() or 0
        context["recent_signals"] = (
            session.query(SignalLog).order_by(SignalLog.created_at.desc()).limit(8).all()
        )
        context["positions"] = (
            session.query(Position).filter(Position.status == "OPEN").order_by(Position.created_at.desc()).limit(8).all()
        )
        context["current_balance"] = round(current_balance(session), 2)
        context["closed_trades"] = (
            session.query(TradeHistory).order_by(TradeHistory.closed_at.desc()).limit(8).all()
        )
    except Exception:
        database_error = "Verilənlər bazası hazırda əlçatan deyil. DATABASE_URL dəyərini yoxlayın."
    finally:
        if session is not None:
            session.close()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            **context,
            "active_page": "dashboard",
            "trading_mode": settings.trading_mode,
            "demo_trading_enabled": settings.demo_trading_enabled,
            "allowed_symbols": settings.allowed_symbols,
            "max_volume": settings.max_volume,
            "risk_per_trade_pct": settings.risk_per_trade_pct,
            "database_error": database_error,
            "as_float": _as_float,
        },
    )


@router.get("/news", response_class=HTMLResponse)
def news_page(request: Request):
    database_error = None
    posts = []
    session: Session | None = None
    try:
        session = next(get_db())
        posts = (
            session.query(NewsPost)
            .filter(NewsPost.status == "PUBLISHED")
            .order_by(NewsPost.approved_at.desc())
            .limit(30)
            .all()
        )
    except Exception:
        database_error = "Verilənlər bazası hazırda əlçatan deyil."
    finally:
        if session is not None:
            session.close()

    return templates.TemplateResponse(
        request,
        "news.html",
        {
            "active_page": "news",
            "posts": posts,
            "database_error": database_error,
        },
    )


@router.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        {"active_page": "about"},
    )


@router.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    stats = {"signals_total": 0, "published_news": 0, "open_positions": 0}
    session: Session | None = None
    try:
        session = next(get_db())
        stats["signals_total"] = session.query(func.count(SignalLog.id)).scalar() or 0
        stats["published_news"] = (
            session.query(func.count(NewsPost.id)).filter(NewsPost.status == "PUBLISHED").scalar() or 0
        )
        stats["open_positions"] = session.query(Position).filter(Position.status == "OPEN").count()
    except Exception:
        pass
    finally:
        if session is not None:
            session.close()

    return templates.TemplateResponse(
        request,
        "pricing.html",
        {"active_page": "pricing", "stats": stats},
    )
