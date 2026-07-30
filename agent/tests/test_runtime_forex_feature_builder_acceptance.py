"""Acceptance tests for the runtime forex Feature Builder only."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest

from src.trading.forex_features import (
    DuplicateBarError,
    InvalidMarketSnapshotError,
    RuntimeFeatureBuilder,
    StaleBarError,
    WarmupStatus,
)

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _bar(index: int, *, close: float | None = None, **overrides: object) -> dict[str, object]:
    price = close if close is not None else 100.0 + index * 0.1
    payload: dict[str, object] = {
        "symbol": "XAUUSD",
        "timeframe": "1h",
        "broker_timestamp": NOW - timedelta(hours=210 - index),
        "validated": True,
        "closed": True,
        "ohlcv": {
            "open": price - 0.2,
            "high": price + 0.5,
            "low": price - 0.6,
            "close": price,
            "volume": 1000.0 + index,
        },
        "spread": 0.2,
        "tick_metadata": {"bid": price - 0.1, "ask": price + 0.1},
    }
    payload.update(overrides)
    return payload


def _builder() -> RuntimeFeatureBuilder:
    return RuntimeFeatureBuilder(clock=lambda: NOW, stale_after=timedelta(days=30))


def test_warmup_exposes_status_and_becomes_ready_at_200_bars() -> None:
    builder = _builder()
    first = builder.build(_bar(0))
    outputs = [builder.build(_bar(index)) for index in range(1, 200)]

    assert first.warmup_status is WarmupStatus.WARMING_UP
    assert first.warmup_bars_seen == 1
    assert first.feature_values["ema_200"] == pytest.approx(100.0)
    assert "atr_14" not in first.feature_values
    assert outputs[-1].warmup_status is WarmupStatus.READY
    assert outputs[-1].warmup_bars_seen == 200
    assert set(("ema_20", "ema_50", "ema_200", "atr_14", "rsi_14", "macd", "macd_signal", "macd_histogram", "volume_sma_20")) <= set(outputs[-1].feature_values)


def test_duplicate_candle_is_rejected_without_mutating_state() -> None:
    builder = _builder()
    original = builder.build(_bar(0))
    with pytest.raises(DuplicateBarError):
        builder.build(_bar(0))
    next_snapshot = builder.build(_bar(1))
    assert next_snapshot.warmup_bars_seen == original.warmup_bars_seen + 1


def test_stale_candle_is_rejected() -> None:
    builder = RuntimeFeatureBuilder(clock=lambda: NOW, stale_after=timedelta(days=1))
    stale = _bar(0, broker_timestamp=NOW - timedelta(days=2))
    with pytest.raises(StaleBarError):
        builder.build(stale)


@pytest.mark.parametrize(
    "changes",
    [
        {"validated": False},
        {"closed": False},
        {"spread": float("nan")},
        {"tick_metadata": None},
        {"ohlcv": {"open": 1.0, "high": 1.0, "low": 1.0, "close": float("inf"), "volume": 1.0}},
    ],
)
def test_invalid_or_nonfinite_snapshot_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(InvalidMarketSnapshotError):
        _builder().build({**_bar(0), **changes})


def test_deterministic_replay_and_canonical_ordering() -> None:
    bars = tuple(_bar(index) for index in range(200))
    first = RuntimeFeatureBuilder(clock=lambda: NOW, stale_after=timedelta(days=30)).replay(bars)
    second = RuntimeFeatureBuilder(clock=lambda: NOW, stale_after=timedelta(days=30)).replay(bars)

    assert tuple(item.canonical_json() for item in first) == tuple(item.canonical_json() for item in second)
    assert tuple(item.digest for item in first) == tuple(item.digest for item in second)
    assert list(first[-1].feature_values) == sorted(first[-1].feature_values)


def test_feature_parity_for_known_causal_sequence() -> None:
    builder = _builder()
    # Constant close makes every EMA equal to close and RSI neutral after warmup.
    outputs = builder.replay(tuple(_bar(index, close=100.0) for index in range(200)))
    final = outputs[-1]

    assert final.feature_values["ema_20"] == pytest.approx(100.0)
    assert final.feature_values["ema_50"] == pytest.approx(100.0)
    assert final.feature_values["ema_200"] == pytest.approx(100.0)
    assert final.feature_values["macd"] == pytest.approx(0.0)
    assert final.feature_values["macd_signal"] == pytest.approx(0.0)
    assert final.feature_values["macd_histogram"] == pytest.approx(0.0)
    assert final.feature_values["rsi_14"] == pytest.approx(50.0)
    assert final.feature_values["atr_14"] == pytest.approx(1.1)
    assert final.feature_values["volume_sma_20"] == pytest.approx(1189.5)


def test_snapshot_is_immutable_and_features_are_frozen() -> None:
    snapshot = _builder().build(_bar(0))
    assert isinstance(snapshot.feature_values, MappingProxyType)
    with pytest.raises((TypeError, ValueError)):
        snapshot.feature_values["ema_20"] = 1.0  # type: ignore[index]
    with pytest.raises((TypeError, ValueError)):
        snapshot.symbol = "EURUSD"  # type: ignore[misc]


def test_bars_must_be_strictly_chronological_per_stream() -> None:
    builder = _builder()
    builder.build(_bar(1))
    with pytest.raises(InvalidMarketSnapshotError):
        builder.build(_bar(0))
