"""Causal, one-candle-at-a-time OHLCV input."""

from __future__ import annotations
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = "XAUUSD"
    timeframe: str = "1h"

    @property
    def validated(self):
        return True

    @property
    def closed(self):
        return True

    @property
    def broker_timestamp(self):
        return self.timestamp

    @property
    def spread(self):
        return 0.0

    @property
    def tick_metadata(self):
        return {"source": "historical_csv"}


class CandleFeed:
    def __init__(self, candles: Iterable[Candle]):
        self._candles = tuple(candles)
        self._index = 0
        self._current = None
        if any(self._candles[i].timestamp >= self._candles[i + 1].timestamp for i in range(len(self._candles) - 1)):
            raise ValueError("candles must be strictly chronological")

    @classmethod
    def from_csv(cls, path, *, symbol="XAUUSD", timeframe="1h"):
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            rows = csv.DictReader(handle)
            required = {"timestamp", "open", "high", "low", "close", "volume"}
            if not required <= set(rows.fieldnames or ()):
                raise ValueError(f"CSV must contain {sorted(required)}")
            return cls(
                Candle(
                    _utc(r["timestamp"]),
                    *(float(r[x]) for x in ("open", "high", "low", "close", "volume")),
                    symbol,
                    timeframe,
                )
                for r in rows
            )

    def next(self):
        if self.finished():
            return None
        self._current = self._candles[self._index]
        self._index += 1
        return self._current

    def current(self):
        return self._current

    def finished(self):
        return self._index >= len(self._candles)

    def length(self):
        return len(self._candles)


def _utc(value):
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
