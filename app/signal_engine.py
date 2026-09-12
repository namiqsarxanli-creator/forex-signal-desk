"""RSI-based signal engine.

Pulls real daily FX closes (Frankfurter/ECB, no API key needed), computes a
Wilder RSI(14) per allowed symbol, and turns oversold/overbought readings
into `TradeSignal`s that flow through the exact same risk + execution
pipeline as `/webhook/signal` (see `app.api.process_signal`).

Two ways to trigger it:
- automatically, every 15 minutes, from the background task started in main.py
- on demand, from `POST /signals/run-now` (used by the dashboard's demo button,
  and importable as an n8n Schedule -> HTTP Request workflow)
"""
import logging

from sqlalchemy.orm import Session

from app.core import settings
from app.market_data import fetch_daily_closes
from app.models import TradeSignal
from app.sizing import STOP_PIPS, TARGET_PIPS, pip_size, size_position
from app.strategies import compute_rsi, decide_action

logger = logging.getLogger(__name__)


def _pip_buffers(symbol: str) -> tuple[float, float]:
    """Stop/target distance in price units, derived from the shared pip counts."""
    size = pip_size(symbol)
    return STOP_PIPS * size, TARGET_PIPS * size


def _build_signal(symbol: str, action: str, last_price: float, rsi: float, volume: float) -> TradeSignal:
    stop_buffer, target_buffer = _pip_buffers(symbol)
    if action == "BUY":
        stop_loss = round(last_price - stop_buffer, 5)
        take_profit = round(last_price + target_buffer, 5)
    else:
        stop_loss = round(last_price + stop_buffer, 5)
        take_profit = round(last_price - target_buffer, 5)

    return TradeSignal(
        symbol=symbol,
        action=action,
        volume=volume,
        source="RSI_ENGINE",
        entry_price=last_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        confidence_score=round(abs(50 - rsi) * 2, 2),  # further from 50 => more confident
    )


def preview_signals() -> list[dict]:
    """Read-only: compute RSI for every allowed symbol without placing any order."""
    readings = []
    for symbol in settings.allowed_symbols:
        closes = fetch_daily_closes(symbol)
        rsi = compute_rsi(closes)
        action = decide_action(rsi)
        readings.append({
            "symbol": symbol,
            "rsi": round(rsi, 1) if rsi is not None else None,
            "last_price": closes[-1] if closes else None,
            "action": action,
            "data_points": len(closes),
        })
    return readings


def run_once(db: Session) -> list[dict]:
    """Compute RSI for every allowed symbol, close any PAPER positions whose

    SL/TP the latest price has crossed, and submit real signals where triggered.
    This is the only place that feeds PAPER positions a "current price" on a
    recurring basis -- without it, positions opened by the RSI engine or the
    public webhook would stay open forever unless someone manually calls
    POST /paper/quote (see app/paper.py).
    """
    from app.api import process_signal  # local import avoids a circular import at module load
    from app.paper import apply_paper_quote

    results = []
    for symbol in settings.allowed_symbols:
        closes = fetch_daily_closes(symbol)
        rsi = compute_rsi(closes)
        action = decide_action(rsi)

        positions_closed = 0
        if closes and settings.trading_mode == "PAPER":
            positions_closed = apply_paper_quote(db, symbol, closes[-1])

        if action is None or rsi is None or not closes:
            results.append({
                "symbol": symbol,
                "rsi": round(rsi, 1) if rsi is not None else None,
                "action": None,
                "message": "No signal (RSI in neutral zone or data unavailable)",
                "positions_closed": positions_closed,
            })
            continue

        volume = size_position(db, symbol, STOP_PIPS)
        signal = _build_signal(symbol, action, closes[-1], rsi, volume)
        try:
            outcome = process_signal(signal, db)
        except Exception as exc:  # keep the loop going even if one symbol fails
            logger.exception("RSI engine failed to submit signal for %s", symbol)
            outcome = {"status": "error", "message": str(exc)}

        results.append({
            "symbol": symbol,
            "rsi": round(rsi, 1),
            "action": action,
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "result": outcome,
            "positions_closed": positions_closed,
        })

    return results
