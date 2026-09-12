"""Free, no-key daily FX price history via the Frankfurter API (ECB reference rates).

Used to feed the RSI signal engine. Frankfurter only publishes one rate per
business day, so this powers a *daily-swing* RSI reading, not intraday
scalping -- which is a perfectly honest and demo-friendly choice: no broker
market-data subscription required to show a real, live-computed indicator.
"""
import logging
from datetime import date, timedelta

import requests

logger = logging.getLogger(__name__)

FRANKFURTER_URL = "https://api.frankfurter.app/{start}..{end}"
REQUEST_TIMEOUT = 8


def split_symbol(symbol: str) -> tuple[str, str]:
    symbol = symbol.upper().strip()
    return symbol[:3], symbol[3:6]


def fetch_daily_series(symbol: str, lookback_days: int = 60) -> list[dict]:
    """Return an oldest-to-newest list of {date, close} for `symbol`.

    `symbol` is a 6-letter FX pair such as EURUSD, GBPUSD, USDJPY.
    Returns an empty list if the data could not be fetched (e.g. offline).
    """
    base, quote = split_symbol(symbol)
    end = date.today()
    start = end - timedelta(days=lookback_days)
    url = FRANKFURTER_URL.format(start=start.isoformat(), end=end.isoformat())

    try:
        response = requests.get(url, params={"from": base, "to": quote}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        logger.warning("Could not fetch FX history for %s", symbol, exc_info=True)
        return []

    rates = payload.get("rates", {})
    return [
        {"date": day, "close": day_rates[quote]}
        for day, day_rates in sorted(rates.items())
        if quote in day_rates
    ]


def fetch_daily_closes(symbol: str, lookback_days: int = 60) -> list[float]:
    """Same data as fetch_daily_series, prices only -- kept for the RSI engine."""
    return [point["close"] for point in fetch_daily_series(symbol, lookback_days)]


def fetch_latest_price(symbol: str) -> float | None:
    closes = fetch_daily_closes(symbol, lookback_days=7)
    return closes[-1] if closes else None
