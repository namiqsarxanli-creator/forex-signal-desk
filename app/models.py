from typing import Literal

from pydantic import BaseModel, Field, validator


class TradeSignal(BaseModel):
    symbol: str = Field(..., min_length=6, max_length=20)
    action: Literal["BUY", "SELL"]
    volume: float = Field(..., gt=0)
    source: str = Field(..., min_length=2, max_length=50)
    entry_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    stop_loss_pips: float | None = Field(default=None, gt=0, le=200)
    take_profit_pips: float | None = Field(default=None, gt=0, le=400)
    confidence_score: float | None = Field(default=None, ge=0, le=100)

    @validator("symbol", "source", pre=True)
    def normalize_text(cls, value: str) -> str:
        return value.strip().upper()

    @validator("action", pre=True)
    def normalize_action(cls, value: str) -> str:
        return value.strip().upper()


class OrderResponse(BaseModel):
    status: str
    message: str
    details: dict


class QuoteUpdate(BaseModel):
    symbol: str = Field(..., min_length=6, max_length=20)
    price: float = Field(..., gt=0)

    @validator("symbol", pre=True)
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class NewsPublishRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=500)
    summary: str = Field(..., min_length=20, max_length=12000)
    source_url: str | None = Field(default=None, max_length=1000)
    instagram_caption: str | None = Field(default=None, max_length=2200)
    image_url: str | None = Field(default=None, max_length=1000)

    @validator("title", "summary", "source_url", "instagram_caption", "image_url", pre=True)
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class NewsDraftRequest(NewsPublishRequest):
    """Same shape as NewsPublishRequest; used by the n8n news-analysis workflow
    to create a DRAFT that a human later approves with /paylas <id>."""


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)
