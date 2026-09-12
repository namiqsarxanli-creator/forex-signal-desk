"""Paper-trading helpers.

Keeps the PAPER mode self-contained: every open paper position is tracked in
``PaperPosition`` (stop_loss / take_profit / last_price). When a simulated
price update arrives via ``POST /paper/quote`` we check whether the price has
crossed the stop_loss or take_profit for that symbol and, if so, close the
position and write a ``TradeHistory`` row so the dashboard can show realized
P/L without ever touching a real broker.
"""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db_models import PaperPosition, Position, TradeHistory


def create_paper_metadata(
    db: Session,
    position: Position,
    stop_loss: float | None,
    take_profit: float | None,
) -> PaperPosition:
    """Attach paper-trading metadata to a freshly filled paper position."""
    metadata = PaperPosition(
        position_id=position.id,
        stop_loss=stop_loss if stop_loss is not None else position.entry_price,
        take_profit=take_profit if take_profit is not None else position.entry_price,
        last_price=position.entry_price,
    )
    db.add(metadata)
    return metadata


def _hit_stop_or_target(order_type: str, price: Decimal, stop_loss: Decimal, take_profit: Decimal) -> str | None:
    if order_type == "BUY":
        if price <= stop_loss:
            return "STOP_LOSS"
        if price >= take_profit:
            return "TAKE_PROFIT"
    else:  # SELL
        if price >= stop_loss:
            return "STOP_LOSS"
        if price <= take_profit:
            return "TAKE_PROFIT"
    return None


def apply_paper_quote(db: Session, symbol: str, price: float) -> int:
    """Update all open paper positions for ``symbol`` with a new price.

    Closes any position whose stop_loss or take_profit was crossed and
    records the realized profit/loss. Returns how many positions closed.
    """
    price_decimal = Decimal(str(price))

    open_positions = (
        db.query(Position)
        .filter(Position.symbol == symbol, Position.status == "OPEN")
        .all()
    )

    closed = 0
    for position in open_positions:
        metadata = (
            db.query(PaperPosition)
            .filter(PaperPosition.position_id == position.id)
            .first()
        )
        if metadata is None:
            continue

        metadata.last_price = price_decimal

        outcome = _hit_stop_or_target(
            position.order_type, price_decimal, metadata.stop_loss, metadata.take_profit
        )
        if outcome is None:
            continue

        exit_price = metadata.stop_loss if outcome == "STOP_LOSS" else metadata.take_profit
        if position.order_type == "BUY":
            profit_loss = (exit_price - position.entry_price) * position.volume
        else:
            profit_loss = (position.entry_price - exit_price) * position.volume

        position.status = "CLOSED"
        db.add(
            TradeHistory(
                position_id=position.id,
                symbol=position.symbol,
                exit_price=exit_price,
                profit_loss=profit_loss,
                closed_at=datetime.now(timezone.utc),
            )
        )
        closed += 1

    db.commit()
    return closed
