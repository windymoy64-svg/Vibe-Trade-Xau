"""Close-confirmed bullish and bearish ACR zone detection."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

from src.trading.auto_selection import OHLCVBar


@dataclass(frozen=True, slots=True)
class ACRInvalidation:
    timestamp: str
    close: float


@dataclass(frozen=True, slots=True)
class ACRZone:
    id: str
    direction: Literal["BULLISH", "BEARISH"]
    status: Literal["FRESH", "INVALID"]
    formed_at: str
    low: float
    high: float
    trigger_close: float
    reference_boundary: float
    invalidation: ACRInvalidation | None


class ACRZoneDetectionService:
    def detect(self, bars: tuple[OHLCVBar, ...] | list[OHLCVBar]) -> tuple[ACRZone, ...]:
        if len(bars) < 2:
            raise ValueError("at least two candles are required for ACR detection")
        zones: list[ACRZone] = []
        for index in range(1, len(bars)):
            reference = bars[index - 1]
            trigger = bars[index]
            if trigger.close > reference.high and trigger.close > trigger.open:
                direction: Literal["BULLISH", "BEARISH"] = "BULLISH"
                boundary = reference.high
            elif trigger.close < reference.low and trigger.close < trigger.open:
                direction = "BEARISH"
                boundary = reference.low
            else:
                continue
            low = min(reference.low, trigger.low)
            high = max(reference.high, trigger.high)
            invalidation = _invalidation(direction, low, high, bars[index + 1:])
            zones.append(ACRZone(
                id=f"acr-{direction.lower()}-{trigger.timestamp.isoformat()}",
                direction=direction,
                status="INVALID" if invalidation else "FRESH",
                formed_at=trigger.timestamp.isoformat(),
                low=round(low, 8),
                high=round(high, 8),
                trigger_close=round(trigger.close, 8),
                reference_boundary=round(boundary, 8),
                invalidation=invalidation,
            ))
        return tuple(zones)


class ACRZoneStatusValidationService:
    """Advance a zone from FRESH to INVALID without allowing reversal."""

    def validate(
        self, zone: ACRZone, bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
    ) -> ACRZone:
        if zone.status == "INVALID":
            return zone
        formed_at = datetime.fromisoformat(zone.formed_at.replace("Z", "+00:00"))
        future = [bar for bar in bars if bar.timestamp > formed_at]
        invalidation = _invalidation(zone.direction, zone.low, zone.high, future)
        return replace(
            zone,
            status="INVALID" if invalidation else "FRESH",
            invalidation=invalidation,
        )


def _invalidation(
    direction: Literal["BULLISH", "BEARISH"],
    low: float,
    high: float,
    future: tuple[OHLCVBar, ...] | list[OHLCVBar],
) -> ACRInvalidation | None:
    for bar in future:
        if (direction == "BULLISH" and bar.close < low) or (
            direction == "BEARISH" and bar.close > high
        ):
            return ACRInvalidation(bar.timestamp.isoformat(), round(bar.close, 8))
    return None
