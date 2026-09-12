import logging

logger = logging.getLogger(__name__)

RSI_PERIOD = 14
RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0


def check_technical_indicators(symbol: str, action: str) -> bool:
    """Legacy placeholder kept for backward compatibility. Prefer `compute_rsi`."""
    logger.info(f"{symbol} üçün texniki indikatorlar (RSI) yoxlanılır...")
    return True


def compute_rsi(closes: list[float], period: int = RSI_PERIOD) -> float | None:
    """Classic Wilder RSI over a list of closing prices (oldest → newest).

    Returns None if there is not enough data (need at least `period + 1` closes).
    """
    if len(closes) < period + 1:
        return None

    gains = []
    losses = []
    for previous, current in zip(closes, closes[1:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def decide_action(rsi: float | None) -> str | None:
    """Simple mean-reversion rule: oversold → BUY, overbought → SELL."""
    if rsi is None:
        return None
    if rsi < RSI_OVERSOLD:
        return "BUY"
    if rsi > RSI_OVERBOUGHT:
        return "SELL"
    return None
