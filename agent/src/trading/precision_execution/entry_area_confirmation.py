"""Generic closed-candle reaction confirmation for entry areas."""

from __future__ import annotations

from typing import Literal

from src.trading.auto_selection import OHLCVBar

ReactionStatus = Literal["WAITING_RETEST", "TOUCHED", "REACTION_CONFIRMED", "INVALIDATED"]


def confirm_area_reaction(
    bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
    *,
    direction: Literal["BULLISH", "BEARISH"],
    low: float,
    high: float,
) -> ReactionStatus:
    """Read only finalized candles; a wick touch alone is not confirmation."""
    if low >= high or not bars:
        return "INVALIDATED"
    latest = bars[-1]
    touched = latest.low <= high and latest.high >= low
    if not touched:
        return "WAITING_RETEST"
    if direction == "BULLISH" and latest.close < low:
        return "INVALIDATED"
    if direction == "BEARISH" and latest.close > high:
        return "INVALIDATED"
    candle_range = latest.high - latest.low
    if candle_range <= 0:
        return "TOUCHED"
    body_low = min(latest.open, latest.close)
    body_high = max(latest.open, latest.close)
    if direction == "BULLISH":
        rejection = latest.close > latest.open and (body_low - latest.low) / candle_range >= 0.4
    else:
        rejection = latest.close < latest.open and (latest.high - body_high) / candle_range >= 0.4
    engulfing = _engulfing(bars, direction)
    return "REACTION_CONFIRMED" if rejection or engulfing else "TOUCHED"


def _engulfing(
    bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
    direction: Literal["BULLISH", "BEARISH"],
) -> bool:
    if len(bars) < 2:
        return False
    previous, current = bars[-2], bars[-1]
    if direction == "BULLISH":
        return previous.close < previous.open and current.close > current.open and current.close >= previous.open
    return previous.close > previous.open and current.close < current.open and current.close <= previous.open
