from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False)
    order_type = Column(String(10), nullable=False)  # BUY / SELL
    volume = Column(Numeric(18, 8), nullable=False)
    entry_price = Column(Numeric(18, 8), nullable=False)
    status = Column(String(20), default="OPEN")  # OPEN / CLOSED
    created_at = Column(DateTime, default=func.now())

    trades = relationship("TradeHistory", back_populates="position")


class PaperPosition(Base):
    __tablename__ = "paper_positions"
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), unique=True, nullable=False)
    stop_loss = Column(Numeric(18, 8), nullable=False)
    take_profit = Column(Numeric(18, 8), nullable=False)
    last_price = Column(Numeric(18, 8), nullable=False)
    created_at = Column(DateTime, default=func.now())


class TradeHistory(Base):
    __tablename__ = "trades_history"
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"))
    symbol = Column(String(50), nullable=False)
    exit_price = Column(Numeric(18, 8), nullable=False)
    profit_loss = Column(Numeric(18, 8), nullable=False)
    closed_at = Column(DateTime, default=func.now())

    position = relationship("Position", back_populates="trades")


class SignalLog(Base):
    __tablename__ = "signal_logs"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False)
    signal_source = Column(String(50), nullable=False)  # TECHNICAL / AI
    action = Column(String(10), nullable=False)
    confidence_score = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime, default=func.now())

class NewsPost(Base):
    __tablename__ = "news_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(String(12000), nullable=False)
    source_url = Column(String(1000), nullable=True)
    instagram_caption = Column(String(2200), nullable=True)
    image_url = Column(String(1000), nullable=True)
    # DRAFT -> created by the n8n news-analysis workflow, visible only to admins/Telegram.
    # PUBLISHED -> approved via /paylas <id>, shown on the public /news page.
    # REJECTED -> explicitly declined, kept for the audit trail.
    status = Column(String(30), nullable=False, default="DRAFT")
    published_at = Column(DateTime, default=func.now())
    approved_at = Column(DateTime, nullable=True)