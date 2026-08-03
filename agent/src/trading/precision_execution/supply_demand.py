"""Mechanical lower-timeframe supply and demand zone detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.trading.auto_selection import OHLCVBar


@dataclass(frozen=True, slots=True)
class SupplyDemandZone:
    id: str
    type: Literal["SUPPLY", "DEMAND"]
    low: float
    high: float
    formed_at: str
    status: Literal["ACTIVE", "TESTED", "INVALID"]
    displacement_ratio: float


class LTFSupplyDemandService:
    def __init__(self, *, lookback: int = 5, displacement_multiplier: float = 1.2) -> None:
        if lookback <= 0 or displacement_multiplier <= 0:
            raise ValueError("zone detection parameters must be positive")
        self.lookback = lookback
        self.displacement_multiplier = displacement_multiplier

    def detect(self, bars: tuple[OHLCVBar, ...] | list[OHLCVBar]) -> tuple[SupplyDemandZone, ...]:
        if len(bars) < self.lookback + 2:
            raise ValueError("insufficient candles for supply/demand detection")
        zones: list[SupplyDemandZone] = []
        for index in range(self.lookback + 1, len(bars)):
            base = bars[index - 1]
            impulse = bars[index]
            ranges = [bar.high - bar.low for bar in bars[index - self.lookback - 1:index - 1]]
            average_range = sum(ranges) / len(ranges)
            body = abs(impulse.close - impulse.open)
            if average_range <= 0 or body < average_range * self.displacement_multiplier:
                continue
            bullish_impulse = impulse.close > impulse.open and base.close <= base.open
            bearish_impulse = impulse.close < impulse.open and base.close >= base.open
            if not bullish_impulse and not bearish_impulse:
                continue
            zone_type: Literal["SUPPLY", "DEMAND"] = "DEMAND" if bullish_impulse else "SUPPLY"
            low = base.low if bullish_impulse else min(base.open, base.close)
            high = max(base.open, base.close) if bullish_impulse else base.high
            status = _zone_status(zone_type, low, high, bars[index + 1:])
            zones.append(SupplyDemandZone(
                id=f"{zone_type.lower()}-{base.timestamp.isoformat()}",
                type=zone_type,
                low=round(low, 8),
                high=round(high, 8),
                formed_at=base.timestamp.isoformat(),
                status=status,
                displacement_ratio=round(body / average_range, 4),
            ))
        return tuple(zones)


def _zone_status(
    zone_type: Literal["SUPPLY", "DEMAND"],
    low: float,
    high: float,
    future: tuple[OHLCVBar, ...] | list[OHLCVBar],
) -> Literal["ACTIVE", "TESTED", "INVALID"]:
    tested = False
    for bar in future:
        if zone_type == "DEMAND":
            if bar.close < low:
                return "INVALID"
            tested = tested or bar.low <= high
        else:
            if bar.close > high:
                return "INVALID"
            tested = tested or bar.high >= low
    return "TESTED" if tested else "ACTIVE"
