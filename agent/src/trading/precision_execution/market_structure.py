"""Confirmed-pivot HTF market structure mapping with BOS/CHOCH events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.trading.auto_selection import OHLCVBar

StructureBias = Literal["BULLISH", "BEARISH", "NEUTRAL"]


@dataclass(frozen=True, slots=True)
class StructureSwing:
    index: int
    timestamp: str
    kind: Literal["HIGH", "LOW"]
    price: float


@dataclass(frozen=True, slots=True)
class StructureBreak:
    index: int
    timestamp: str
    kind: Literal["BOS", "CHOCH"]
    direction: Literal["BULLISH", "BEARISH"]
    broken_price: float


@dataclass(frozen=True, slots=True)
class MarketStructureMap:
    bias: StructureBias
    swings: tuple[StructureSwing, ...]
    breaks: tuple[StructureBreak, ...]


class HTFMarketStructureService:
    def __init__(self, *, pivot_span: int = 2) -> None:
        if pivot_span <= 0:
            raise ValueError("pivot span must be positive")
        self.pivot_span = pivot_span

    def map(self, bars: tuple[OHLCVBar, ...] | list[OHLCVBar]) -> MarketStructureMap:
        if len(bars) < (self.pivot_span * 2) + 1:
            raise ValueError("insufficient candles for confirmed market structure")
        swings = _confirmed_swings(bars, self.pivot_span)
        latest_high: StructureSwing | None = None
        latest_low: StructureSwing | None = None
        consumed: set[tuple[str, int]] = set()
        breaks: list[StructureBreak] = []
        bias: StructureBias = "NEUTRAL"

        swings_by_confirmation: dict[int, list[StructureSwing]] = {}
        for swing in swings:
            swings_by_confirmation.setdefault(swing.index + self.pivot_span, []).append(swing)
        for index, bar in enumerate(bars):
            for swing in swings_by_confirmation.get(index, []):
                if swing.kind == "HIGH":
                    latest_high = swing
                else:
                    latest_low = swing
            if latest_high and ("HIGH", latest_high.index) not in consumed and bar.close > latest_high.price:
                kind = "CHOCH" if bias == "BEARISH" else "BOS"
                breaks.append(StructureBreak(
                    index, bar.timestamp.isoformat(), kind, "BULLISH", latest_high.price,
                ))
                consumed.add(("HIGH", latest_high.index))
                bias = "BULLISH"
            if latest_low and ("LOW", latest_low.index) not in consumed and bar.close < latest_low.price:
                kind = "CHOCH" if bias == "BULLISH" else "BOS"
                breaks.append(StructureBreak(
                    index, bar.timestamp.isoformat(), kind, "BEARISH", latest_low.price,
                ))
                consumed.add(("LOW", latest_low.index))
                bias = "BEARISH"
        return MarketStructureMap(bias, tuple(swings), tuple(breaks))


def _confirmed_swings(
    bars: tuple[OHLCVBar, ...] | list[OHLCVBar], span: int,
) -> list[StructureSwing]:
    swings: list[StructureSwing] = []
    for index in range(span, len(bars) - span):
        bar = bars[index]
        neighbors = [*bars[index - span:index], *bars[index + 1:index + span + 1]]
        if all(bar.high > neighbor.high for neighbor in neighbors):
            swings.append(StructureSwing(index, bar.timestamp.isoformat(), "HIGH", bar.high))
        if all(bar.low < neighbor.low for neighbor in neighbors):
            swings.append(StructureSwing(index, bar.timestamp.isoformat(), "LOW", bar.low))
    return swings
