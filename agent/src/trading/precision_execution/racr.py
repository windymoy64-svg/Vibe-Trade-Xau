"""Liquidity-sweep and reclaim detection for R-ACR reversal signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.trading.auto_selection import OHLCVBar


@dataclass(frozen=True, slots=True)
class RACRReversalSignal:
    timestamp: str
    direction: Literal["BULLISH", "BEARISH"]
    close: float
    sweep_price: float
    reclaimed_level: float


class RACRReversalDetectionService:
    def __init__(self, *, lookback: int = 3) -> None:
        if lookback <= 0:
            raise ValueError("R-ACR lookback must be positive")
        self.lookback = lookback

    def detect(self, bars: tuple[OHLCVBar, ...] | list[OHLCVBar]) -> tuple[RACRReversalSignal, ...]:
        if len(bars) <= self.lookback:
            raise ValueError("insufficient candles for R-ACR detection")
        signals: list[RACRReversalSignal] = []
        for index in range(self.lookback, len(bars)):
            candle = bars[index]
            reference = bars[index - self.lookback:index]
            prior_low = min(bar.low for bar in reference)
            prior_high = max(bar.high for bar in reference)
            if candle.low < prior_low and candle.close > prior_low and candle.close > candle.open:
                signals.append(RACRReversalSignal(
                    candle.timestamp.isoformat(), "BULLISH", candle.close,
                    candle.low, prior_low,
                ))
            elif candle.high > prior_high and candle.close < prior_high and candle.close < candle.open:
                signals.append(RACRReversalSignal(
                    candle.timestamp.isoformat(), "BEARISH", candle.close,
                    candle.high, prior_high,
                ))
        return tuple(signals)
