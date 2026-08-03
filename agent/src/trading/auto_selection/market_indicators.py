"""Incremental market indicators for real-time strategy selection."""

from __future__ import annotations

import math
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Trend = Literal["BULLISH", "BEARISH", "NEUTRAL", "UNKNOWN"]
Volatility = Literal["LOW", "NORMAL", "HIGH", "UNKNOWN"]
MarketRegime = Literal["TRENDING", "RANGING", "BREAKOUT", "TRANSITION", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class OHLCVBar:
    """One finalized or in-progress OHLCV candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        values = (self.open, self.high, self.low, self.close, self.volume)
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        if not all(math.isfinite(value) for value in values):
            raise ValueError("OHLCV values must be finite")
        if self.volume < 0:
            raise ValueError("volume must not be negative")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must contain the candle range")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must contain the candle range")


@dataclass(frozen=True, slots=True)
class MarketIndicatorSnapshot:
    """Immutable indicator state emitted after each candle update."""

    symbol: str
    timeframe: str
    timestamp: datetime
    bar_count: int
    ready: bool
    close: float
    ema_fast: float | None
    ema_slow: float | None
    rsi: float | None
    atr: float | None
    volume_ratio: float | None
    trend: Trend
    volatility: Volatility
    regime: MarketRegime


class RealtimeMarketIndicatorService:
    """Maintain a bounded candle stream and calculate indicators on update.

    Re-sending the latest timestamp replaces its in-progress candle. Older
    timestamps are rejected so a live feed cannot silently corrupt ordering.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        *,
        fast_ema_period: int = 9,
        slow_ema_period: int = 21,
        rsi_period: int = 14,
        atr_period: int = 14,
        volume_period: int = 20,
        max_bars: int = 500,
        trend_threshold_pct: float = 0.05,
        low_volatility_pct: float = 0.08,
        high_volatility_pct: float = 0.30,
    ) -> None:
        normalized_symbol = str(symbol or "").strip().upper()
        normalized_timeframe = str(timeframe or "").strip().upper()
        periods = (fast_ema_period, slow_ema_period, rsi_period, atr_period, volume_period)
        required_bars = max(slow_ema_period, rsi_period + 1, atr_period + 1, volume_period)
        if not normalized_symbol or not normalized_timeframe:
            raise ValueError("symbol and timeframe are required")
        if any(period <= 0 for period in periods):
            raise ValueError("indicator periods must be positive")
        if fast_ema_period >= slow_ema_period:
            raise ValueError("fast EMA period must be lower than slow EMA period")
        if max_bars < required_bars:
            raise ValueError(f"max_bars must be at least {required_bars}")
        if not 0 <= low_volatility_pct < high_volatility_pct:
            raise ValueError("volatility thresholds must be ordered and non-negative")
        if trend_threshold_pct < 0:
            raise ValueError("trend threshold must not be negative")

        self.symbol = normalized_symbol
        self.timeframe = normalized_timeframe
        self.fast_ema_period = fast_ema_period
        self.slow_ema_period = slow_ema_period
        self.rsi_period = rsi_period
        self.atr_period = atr_period
        self.volume_period = volume_period
        self.trend_threshold_pct = trend_threshold_pct
        self.low_volatility_pct = low_volatility_pct
        self.high_volatility_pct = high_volatility_pct
        self._bars: deque[OHLCVBar] = deque(maxlen=max_bars)
        self._lock = threading.RLock()
        self._snapshot: MarketIndicatorSnapshot | None = None

    @property
    def snapshot(self) -> MarketIndicatorSnapshot | None:
        """Return the latest immutable snapshot, if any."""
        with self._lock:
            return self._snapshot

    def update(self, bar: OHLCVBar) -> MarketIndicatorSnapshot:
        """Append or replace the latest candle and return fresh indicators."""
        with self._lock:
            if self._bars and bar.timestamp < self._bars[-1].timestamp:
                raise ValueError("bar timestamp must not move backwards")
            if self._bars and bar.timestamp == self._bars[-1].timestamp:
                self._bars[-1] = bar
            else:
                self._bars.append(bar)
            self._snapshot = self._calculate_snapshot()
            return self._snapshot

    def extend(self, bars: list[OHLCVBar] | tuple[OHLCVBar, ...]) -> MarketIndicatorSnapshot:
        """Apply an ordered batch and return the final snapshot."""
        if not bars:
            raise ValueError("bars must not be empty")
        snapshot: MarketIndicatorSnapshot | None = None
        for bar in bars:
            snapshot = self.update(bar)
        assert snapshot is not None
        return snapshot

    def _calculate_snapshot(self) -> MarketIndicatorSnapshot:
        bars = list(self._bars)
        closes = [bar.close for bar in bars]
        volumes = [bar.volume for bar in bars]
        ema_fast = _ema(closes, self.fast_ema_period)
        ema_slow = _ema(closes, self.slow_ema_period)
        rsi = _rsi(closes, self.rsi_period)
        atr = _atr(bars, self.atr_period)
        volume_ratio = _volume_ratio(volumes, self.volume_period)
        ready = all(value is not None for value in (ema_fast, ema_slow, rsi, atr, volume_ratio))
        trend = self._classify_trend(ema_fast, ema_slow)
        volatility = self._classify_volatility(atr, closes[-1])
        regime = _classify_regime(ready, trend, volatility)
        return MarketIndicatorSnapshot(
            symbol=self.symbol,
            timeframe=self.timeframe,
            timestamp=bars[-1].timestamp,
            bar_count=len(bars),
            ready=ready,
            close=round(closes[-1], 8),
            ema_fast=_rounded(ema_fast),
            ema_slow=_rounded(ema_slow),
            rsi=_rounded(rsi),
            atr=_rounded(atr),
            volume_ratio=_rounded(volume_ratio),
            trend=trend,
            volatility=volatility,
            regime=regime,
        )

    def _classify_trend(self, ema_fast: float | None, ema_slow: float | None) -> Trend:
        if ema_fast is None or ema_slow is None or ema_slow == 0:
            return "UNKNOWN"
        difference_pct = ((ema_fast - ema_slow) / abs(ema_slow)) * 100
        if difference_pct > self.trend_threshold_pct:
            return "BULLISH"
        if difference_pct < -self.trend_threshold_pct:
            return "BEARISH"
        return "NEUTRAL"

    def _classify_volatility(self, atr: float | None, close: float) -> Volatility:
        if atr is None or close == 0:
            return "UNKNOWN"
        atr_pct = (atr / abs(close)) * 100
        if atr_pct < self.low_volatility_pct:
            return "LOW"
        if atr_pct > self.high_volatility_pct:
            return "HIGH"
        return "NORMAL"


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    current = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for value in values[period:]:
        current = ((value - current) * multiplier) + current
    return current


def _rsi(closes: list[float], period: int) -> float | None:
    if len(closes) < period + 1:
        return None
    changes = [current - previous for previous, current in zip(closes, closes[1:])]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
    if average_gain == 0 and average_loss == 0:
        return 50.0
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def _atr(bars: list[OHLCVBar], period: int) -> float | None:
    if len(bars) < period + 1:
        return None
    ranges = [
        max(bar.high - bar.low, abs(bar.high - previous.close), abs(bar.low - previous.close))
        for previous, bar in zip(bars, bars[1:])
    ]
    current = sum(ranges[:period]) / period
    for true_range in ranges[period:]:
        current = ((current * (period - 1)) + true_range) / period
    return current


def _volume_ratio(volumes: list[float], period: int) -> float | None:
    if len(volumes) < period:
        return None
    average = sum(volumes[-period:]) / period
    if average == 0:
        return 1.0
    return volumes[-1] / average


def _classify_regime(ready: bool, trend: Trend, volatility: Volatility) -> MarketRegime:
    if not ready:
        return "UNKNOWN"
    if volatility == "HIGH":
        return "BREAKOUT"
    if trend in ("BULLISH", "BEARISH") and volatility == "NORMAL":
        return "TRENDING"
    if trend == "NEUTRAL" and volatility in ("LOW", "NORMAL"):
        return "RANGING"
    return "TRANSITION"


def _rounded(value: float | None) -> float | None:
    return round(value, 8) if value is not None else None
