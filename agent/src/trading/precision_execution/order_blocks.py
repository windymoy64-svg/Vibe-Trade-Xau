"""Closed-candle, structure-confirmed Order Block detection."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from src.trading.auto_selection import OHLCVBar
from .market_structure import MarketStructureMap

OrderBlockDirection = Literal["BULLISH", "BEARISH"]
OrderBlockStatus = Literal["FRESH", "PARTIALLY_MITIGATED", "MITIGATED", "INVALID"]


@dataclass(frozen=True, slots=True)
class OrderBlock:
    id: str
    direction: OrderBlockDirection
    status: OrderBlockStatus
    origin_index: int
    origin_timestamp: str
    displacement_index: int
    displacement_timestamp: str
    low: float
    high: float
    structure_break_kind: Literal["BOS", "CHOCH"]
    broken_swing_price: float
    displacement_ratio: float
    mitigation_count: int


class OrderBlockDetectionService:
    """Find the last opposing candle before a confirmed structural break.

    The service only consumes the supplied, already-closed bars. A wick through
    a zone does not invalidate it; invalidation requires an opposite close.
    """

    def __init__(
        self,
        *,
        origin_search: int = 3,
        displacement_multiplier: float = 1.2,
        max_mitigations: int = 2,
    ) -> None:
        if origin_search <= 0 or displacement_multiplier <= 0 or max_mitigations <= 0:
            raise ValueError("Order Block parameters must be positive")
        self.origin_search = origin_search
        self.displacement_multiplier = displacement_multiplier
        self.max_mitigations = max_mitigations

    def detect(
        self,
        bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
        structure: MarketStructureMap,
    ) -> tuple[OrderBlock, ...]:
        if len(bars) < 3:
            raise ValueError("at least three candles are required for Order Block detection")
        blocks: list[OrderBlock] = []
        for break_event in structure.breaks:
            displacement_index = break_event.index
            if displacement_index <= 0 or displacement_index >= len(bars):
                continue
            origin_index = self._find_origin(bars, displacement_index, break_event.direction)
            if origin_index is None:
                continue
            displacement = bars[displacement_index]
            lookback = bars[max(0, origin_index - 5):origin_index]
            average_range = sum(bar.high - bar.low for bar in lookback) / len(lookback) if lookback else 0.0
            body = abs(displacement.close - displacement.open)
            if average_range <= 0 or body < average_range * self.displacement_multiplier:
                continue
            origin = bars[origin_index]
            direction: OrderBlockDirection = break_event.direction
            low, high = origin.low, origin.high
            status, mitigation_count = _status(
                direction, low, high, bars[displacement_index + 1:], self.max_mitigations,
            )
            blocks.append(OrderBlock(
                id=f"ob-{direction.lower()}-{origin.timestamp.isoformat()}-{break_event.timestamp}",
                direction=direction,
                status=status,
                origin_index=origin_index,
                origin_timestamp=origin.timestamp.isoformat(),
                displacement_index=displacement_index,
                displacement_timestamp=displacement.timestamp.isoformat(),
                low=round(low, 8),
                high=round(high, 8),
                structure_break_kind=break_event.kind,
                broken_swing_price=round(break_event.broken_price, 8),
                displacement_ratio=round(body / average_range, 4),
                mitigation_count=mitigation_count,
            ))
        return tuple(blocks)

    def validate(
        self,
        block: OrderBlock,
        bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
    ) -> OrderBlock:
        if block.status == "INVALID":
            return block
        start = block.displacement_index + 1
        status, count = _status(
            block.direction, block.low, block.high, tuple(bars)[start:], self.max_mitigations,
        )
        return replace(block, status=status, mitigation_count=count)

    def _find_origin(
        self,
        bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
        displacement_index: int,
        direction: Literal["BULLISH", "BEARISH"],
    ) -> int | None:
        for index in range(displacement_index - 1, max(-1, displacement_index - self.origin_search - 1), -1):
            bar = bars[index]
            if (direction == "BULLISH" and bar.close <= bar.open) or (
                direction == "BEARISH" and bar.close >= bar.open
            ):
                return index
        return None


def _status(
    direction: OrderBlockDirection,
    low: float,
    high: float,
    future: tuple[OHLCVBar, ...] | list[OHLCVBar],
    max_mitigations: int,
) -> tuple[OrderBlockStatus, int]:
    mitigation_count = 0
    for bar in future:
        if (direction == "BULLISH" and bar.close < low) or (
            direction == "BEARISH" and bar.close > high
        ):
            return "INVALID", mitigation_count
        touched = bar.low <= high if direction == "BULLISH" else bar.high >= low
        if touched:
            mitigation_count += 1
    if mitigation_count == 0:
        return "FRESH", 0
    if mitigation_count >= max_mitigations:
        return "MITIGATED", mitigation_count
    return "PARTIALLY_MITIGATED", mitigation_count
