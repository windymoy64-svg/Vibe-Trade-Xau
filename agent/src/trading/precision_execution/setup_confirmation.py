"""Retest/rebound lifecycle checks for closed-candle execution setups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.trading.auto_selection import OHLCVBar
from .acr_zones import ACRZone

SetupState = Literal[
    "RETEST_WAITING", "REBOUND_CONFIRMED", "INVALIDATED", "EXPIRED", "TOO_MANY_TOUCHES",
]


@dataclass(frozen=True, slots=True)
class SetupConfirmation:
    state: SetupState
    touch_count: int
    age_candles: int
    rejection_confirmed: bool
    reason: str


def evaluate_setup(
    zone: ACRZone,
    bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
    *,
    max_retest_candles: int = 24,
    max_zone_touches: int = 2,
) -> SetupConfirmation:
    """Evaluate one ACR setup without looking at an in-progress candle."""
    if max_retest_candles <= 0 or max_zone_touches <= 0:
        raise ValueError("setup lifecycle limits must be positive")
    ordered = tuple(bars)
    formed_index = next(
        (index for index, bar in enumerate(ordered) if bar.timestamp.isoformat() == zone.formed_at),
        None,
    )
    if formed_index is None:
        raise ValueError("zone formation candle is not present in bars")
    future = ordered[formed_index + 1:]
    age = len(future)
    touches = sum(_touches_zone(bar, zone.low, zone.high) for bar in future)
    if zone.status == "INVALID":
        return SetupConfirmation("INVALIDATED", touches, age, False, "ACR zone is invalidated.")
    if age > max_retest_candles:
        return SetupConfirmation("EXPIRED", touches, age, False, "Retest window expired.")
    if touches > max_zone_touches:
        return SetupConfirmation("TOO_MANY_TOUCHES", touches, age, False, "Zone exceeded the maximum touch count.")
    last = ordered[-1]
    last_touched = _touches_zone(last, zone.low, zone.high)
    rejection = last_touched and is_rejection_candle(last, zone.direction, zone.low, zone.high)
    engulfing = last_touched and is_engulfing_candle(ordered, zone.direction)
    if rejection or engulfing:
        return SetupConfirmation(
            "REBOUND_CONFIRMED", touches, age, True,
            "Rejection candle confirmed the zone rebound." if rejection else "Engulfing candle confirmed the zone rebound.",
        )
    return SetupConfirmation("RETEST_WAITING", touches, age, False, "Waiting for a retest rejection or engulfing confirmation.")


def is_rejection_candle(
    bar: OHLCVBar,
    direction: Literal["BULLISH", "BEARISH"],
    zone_low: float,
    zone_high: float,
    *,
    minimum_wick_ratio: float = 0.4,
) -> bool:
    candle_range = bar.high - bar.low
    if candle_range <= 0 or not (bar.low <= zone_high and bar.high >= zone_low):
        return False
    body = abs(bar.close - bar.open)
    if direction == "BULLISH":
        return bar.close > bar.open and (min(bar.open, bar.close) - bar.low) / candle_range >= minimum_wick_ratio and bar.close >= zone_high
    return bar.close < bar.open and (bar.high - max(bar.open, bar.close)) / candle_range >= minimum_wick_ratio and bar.close <= zone_low


def is_engulfing_candle(
    bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
    direction: Literal["BULLISH", "BEARISH"],
) -> bool:
    if len(bars) < 2:
        return False
    previous, current = bars[-2], bars[-1]
    if direction == "BULLISH":
        return (
            previous.close < previous.open and current.close > current.open
            and current.open <= previous.close and current.close >= previous.open
        )
    return (
        previous.close > previous.open and current.close < current.open
        and current.open >= previous.close and current.close <= previous.open
    )


def _touches_zone(bar: OHLCVBar, low: float, high: float) -> bool:
    return bar.low <= high and bar.high >= low
