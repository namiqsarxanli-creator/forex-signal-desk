import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    project_name: str = "Forex Trading Bot"
    trading_mode: str = os.getenv("TRADING_MODE", "PAPER").upper()
    demo_trading_enabled: bool = _env_bool("DEMO_TRADING_ENABLED", False)
    live_trading_enabled: bool = _env_bool("LIVE_TRADING_ENABLED", False)
    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{Path(__file__).resolve().parents[1] / 'trading.db'}"
    )
    allowed_symbols: tuple[str, ...] = tuple(
        item.strip().upper()
        for item in os.getenv("ALLOWED_SYMBOLS", "EURUSD,GBPUSD,USDJPY").split(",")
        if item.strip()
    )
    max_volume: float = float(os.getenv("MAX_VOLUME", "2.0"))  # absolute safety ceiling, not the typical size
    risk_per_trade_pct: float = float(os.getenv("RISK_PER_TRADE_PCT", "1.0"))
    max_open_positions_per_symbol: int = int(os.getenv("MAX_OPEN_POSITIONS_PER_SYMBOL", "1"))
    mt5_login: int = int(os.getenv("MT5_LOGIN", "0"))
    mt5_password: str = os.getenv("MT5_PASSWORD", "")
    mt5_server: str = os.getenv("MT5_SERVER", "")
    mt5_path: str = os.getenv("MT5_PATH", "").strip()
    groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()

    @property
    def is_demo_server(self) -> bool:
        return "demo" in self.mt5_server.lower()

    @property
    def can_send_mt5_demo_orders(self) -> bool:
        return (
            self.trading_mode == "DEMO"
            and self.demo_trading_enabled
            and self.is_demo_server
            and bool(self.mt5_login and self.mt5_password)
        )


settings = Settings()
