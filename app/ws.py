import json
import logging

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.db_models import TradeHistory

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks connected dashboard clients and fan-outs live JSON ticks to all of them."""

    def __init__(self) -> None:
        self.active: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        if not self.active:
            return
        payload = json.dumps(message, default=str)
        dead = []
        for websocket in list(self.active):
            try:
                await websocket.send_text(payload)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(websocket)


manager = ConnectionManager()


async def broadcast_closed_trades(db: Session, symbol: str, count: int) -> None:
    """Tell every connected dashboard about trades a PAPER price update just closed."""
    if count <= 0:
        return
    trades = (
        db.query(TradeHistory)
        .filter(TradeHistory.symbol == symbol)
        .order_by(TradeHistory.closed_at.desc())
        .limit(count)
        .all()
    )
    for trade in trades:
        await manager.broadcast({
            "type": "trade_closed",
            "symbol": trade.symbol,
            "profit_loss": float(trade.profit_loss),
        })
