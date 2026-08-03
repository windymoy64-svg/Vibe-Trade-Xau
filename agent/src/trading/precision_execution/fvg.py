"""Three-candle Fair Value Gap detection and fill tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.trading.auto_selection import OHLCVBar


@dataclass(frozen=True, slots=True)
class FairValueGap:
    id: str
    direction: Literal["BULLISH", "BEARISH"]
    status: Literal["OPEN", "PARTIAL", "FILLED"]
    formed_at: str
    low: float
    high: float
    fill_percentage: float


class FairValueGapDetectionService:
    def __init__(self, *, minimum_gap: float = 0.0) -> None:
        if minimum_gap < 0:
            raise ValueError("minimum gap must not be negative")
        self.minimum_gap = minimum_gap

    def detect(self, bars: tuple[OHLCVBar, ...] | list[OHLCVBar]) -> tuple[FairValueGap, ...]:
        if len(bars) < 3:
            raise ValueError("at least three candles are required for FVG detection")
        gaps: list[FairValueGap] = []
        for index in range(2, len(bars)):
            first, third = bars[index - 2], bars[index]
            if third.low > first.high and third.low - first.high >= self.minimum_gap:
                direction: Literal["BULLISH", "BEARISH"] = "BULLISH"
                low, high = first.high, third.low
            elif third.high < first.low and first.low - third.high >= self.minimum_gap:
                direction = "BEARISH"
                low, high = third.high, first.low
            else:
                continue
            status, fill = _fill_status(direction, low, high, bars[index + 1:])
            gaps.append(FairValueGap(
                id=f"fvg-{direction.lower()}-{third.timestamp.isoformat()}",
                direction=direction,
                status=status,
                formed_at=third.timestamp.isoformat(),
                low=round(low, 8),
                high=round(high, 8),
                fill_percentage=round(fill, 2),
            ))
        return tuple(gaps)


def _fill_status(
    direction: Literal["BULLISH", "BEARISH"], low: float, high: float,
    future: tuple[OHLCVBar, ...] | list[OHLCVBar],
) -> tuple[Literal["OPEN", "PARTIAL", "FILLED"], float]:
    size = high - low
    maximum_fill = 0.0
    for bar in future:
        if direction == "BULLISH":
            maximum_fill = max(maximum_fill, min(1.0, max(0.0, (high - bar.low) / size)))
        else:
            maximum_fill = max(maximum_fill, min(1.0, max(0.0, (bar.high - low) / size)))
    if maximum_fill >= 1.0:
        return "FILLED", 100.0
    if maximum_fill > 0:
        return "PARTIAL", maximum_fill * 100
    return "OPEN", 0.0
