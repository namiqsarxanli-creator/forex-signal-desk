"""Balance-aware position sizing, shared by every signal source.

Every trade risks a fixed percentage of the *current* PAPER balance
(RISK_PER_TRADE_PCT) rather than always using the same fixed lot size --
as the account grows or shrinks, the lot size grown or shrinks with it.
MAX_VOLUME stays as an absolute safety ceiling so a sizing bug (or a very
large balance) can never produce a reckless order.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import settings
from app.db_models import TradeHistory

STARTING_BALANCE = 10_000.0
STOP_PIPS = 30
TARGET_PIPS = 60
MIN_LOT = 0.01


def pip_size(symbol: str) -> float:
    return 0.01 if symbol.endswith("JPY") else 0.0001


def pip_value_per_lot(symbol: str) -> float:
    # Approximate USD value of 1 pip on a 1.0 standard lot -- a planning
    # estimate, not a live broker quote (see risk-calculator.js for the same rule).
    return 9.1 if symbol.endswith("JPY") else 10.0


def current_balance(db: Session) -> float:
    total_pl = db.query(func.sum(TradeHistory.profit_loss)).scalar() or 0
    return STARTING_BALANCE + float(total_pl)


def size_position(db: Session, symbol: str, stop_loss_pips: float = STOP_PIPS) -> float:
    """Risk-based lot size for `symbol`, scaled to the current PAPER balance."""
    balance = current_balance(db)
    risk_amount = balance * (settings.risk_per_trade_pct / 100)
    raw_lots = risk_amount / (stop_loss_pips * pip_value_per_lot(symbol))
    lots = round(raw_lots, 2)
    return max(MIN_LOT, min(lots, settings.max_volume))
