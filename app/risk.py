from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import settings
from app.db_models import Position
from app.models import TradeSignal


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


def validate_signal_risk(
    signal: TradeSignal, db: Session, live_open_position_count: int | None = None
) -> RiskDecision:
    if signal.symbol not in settings.allowed_symbols:
        return RiskDecision(False, f"Symbol is not allowed: {signal.symbol}")
    if signal.volume > settings.max_volume:
        return RiskDecision(False, f"Volume exceeds MAX_VOLUME ({settings.max_volume})")
    if signal.stop_loss is None and signal.stop_loss_pips is None:
        return RiskDecision(False, "A stop_loss or stop_loss_pips value is required for every trade")
    if signal.action == "BUY" and signal.entry_price and signal.stop_loss >= signal.entry_price:
        return RiskDecision(False, "BUY stop_loss must be below entry_price")
    if signal.action == "SELL" and signal.entry_price and signal.stop_loss <= signal.entry_price:
        return RiskDecision(False, "SELL stop_loss must be above entry_price")
    if signal.take_profit is None and signal.take_profit_pips is None:
        return RiskDecision(False, "A take_profit or take_profit_pips value is required for every trade")

    open_count = live_open_position_count
    if open_count is None:
        open_count = (
            db.query(Position)
            .filter(Position.symbol == signal.symbol, Position.status == "OPEN")
            .count()
        )
    if open_count >= settings.max_open_positions_per_symbol:
        return RiskDecision(False, "Maximum open positions reached for this symbol")
    return RiskDecision(True, "Risk checks passed")
