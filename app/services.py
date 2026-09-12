import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.core import settings
from app.models import TradeSignal

logger = logging.getLogger(__name__)


def get_demo_open_position_count(symbol: str) -> int:
    """Read the broker's current demo positions so stale local rows cannot block trades."""
    if not settings.can_send_mt5_demo_orders:
        raise RuntimeError("Demo trading is not enabled or MT5 demo credentials are invalid.")
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 package is not installed.") from exc

    initialize_args = {"path": settings.mt5_path} if settings.mt5_path else {}
    if not mt5.initialize(**initialize_args):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        if not mt5.login(settings.mt5_login, password=settings.mt5_password, server=settings.mt5_server):
            raise RuntimeError(f"MT5 demo login failed: {mt5.last_error()}")
        return len(mt5.positions_get(symbol=symbol) or ())
    finally:
        mt5.shutdown()


def execute_order(signal: TradeSignal) -> dict:
    """Record paper fills or send orders only to an explicitly confirmed MT5 demo server."""
    if settings.trading_mode == "PAPER":
        if signal.entry_price is None:
            return {
                "status": "rejected",
                "message": "PAPER mode requires entry_price; no order was sent.",
            }
        if signal.stop_loss is None or signal.take_profit is None:
            return {
                "status": "rejected",
                "message": "PAPER mode requires explicit stop_loss and take_profit prices.",
            }
        return {
            "status": "PAPER_FILLED",
            "ticket": f"paper-{uuid4().hex[:12]}",
            "symbol": signal.symbol,
            "type": signal.action,
            "volume": signal.volume,
            "price": signal.entry_price,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    if settings.trading_mode != "DEMO":
        return {"status": "rejected", "message": "Only PAPER and confirmed DEMO modes are supported."}

    if not settings.can_send_mt5_demo_orders:
        return {
            "status": "rejected",
            "message": "Demo trading is not enabled or the configured MT5 server is not a demo server.",
        }

    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {"status": "error", "message": "MetaTrader5 package is not installed."}

    initialize_args = {"path": settings.mt5_path} if settings.mt5_path else {}
    if not mt5.initialize(**initialize_args):
        return {"status": "error", "message": f"MT5 initialization failed: {mt5.last_error()}"}

    try:
        if not mt5.login(settings.mt5_login, password=settings.mt5_password, server=settings.mt5_server):
            return {"status": "error", "message": f"MT5 demo login failed: {mt5.last_error()}"}
        if not mt5.symbol_select(signal.symbol, True):
            return {"status": "error", "message": f"Symbol unavailable: {signal.symbol}"}
        tick = mt5.symbol_info_tick(signal.symbol)
        if tick is None:
            return {"status": "error", "message": "No current price available"}
        price = tick.ask if signal.action == "BUY" else tick.bid
        symbol_info = mt5.symbol_info(signal.symbol)
        if symbol_info is None:
            return {"status": "error", "message": "Symbol information unavailable"}
        pip_size = symbol_info.point * (10 if symbol_info.digits in (3, 5) else 1)
        stop_loss = signal.stop_loss
        take_profit = signal.take_profit
        if signal.stop_loss_pips is not None:
            stop_loss = price - signal.stop_loss_pips * pip_size if signal.action == "BUY" else price + signal.stop_loss_pips * pip_size
        if signal.take_profit_pips is not None:
            take_profit = price + signal.take_profit_pips * pip_size if signal.action == "BUY" else price - signal.take_profit_pips * pip_size
        order_type = mt5.ORDER_TYPE_BUY if signal.action == "BUY" else mt5.ORDER_TYPE_SELL
        result = mt5.order_send({
            "action": mt5.TRADE_ACTION_DEAL, "symbol": signal.symbol, "volume": signal.volume,
            "type": order_type, "price": price, "sl": stop_loss or 0.0,
            "tp": take_profit or 0.0, "deviation": 20, "magic": 234000,
            "comment": "n8n Forex Bot", "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        })
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"status": "failed", "message": getattr(result, "comment", "MT5 order failed")}
        return {"status": "FILLED", "ticket": result.order, "symbol": signal.symbol,
                "type": signal.action, "volume": signal.volume, "price": result.price}
    finally:
        mt5.shutdown()
