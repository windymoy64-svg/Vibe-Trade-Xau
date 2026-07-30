"""Acceptance tests for the deterministic Runtime Forex Signal Engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.trading.forex_features import FEATURE_VERSION, FeatureParameters, FeatureSnapshot, WarmupStatus
from src.trading.forex_signals import (
    STRATEGY_NAME,
    STRATEGY_VERSION,
    DuplicateFeatureSnapshotError,
    InvalidFeatureSnapshotError,
    RuntimeSignalEngine,
    SignalType,
    StaleFeatureSnapshotError,
)

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


def _feature(
    index: int,
    *,
    ema20: float = 110.0,
    ema50: float = 105.0,
    ema200: float = 100.0,
    histogram: float = 1.0,
    rsi: float = 65.0,
    warmup: WarmupStatus = WarmupStatus.READY,
    feature_version: str = FEATURE_VERSION,
) -> FeatureSnapshot:
    return FeatureSnapshot(
        symbol="XAUUSD",
        timeframe="1h",
        broker_timestamp=NOW - timedelta(hours=10 - index),
        feature_version=feature_version,
        parameter_fingerprint=FeatureParameters().fingerprint,
        warmup_status=warmup,
        warmup_bars_seen=200 + index,
        warmup_bars_required=200,
        feature_values={
            "ema_20": ema20,
            "ema_50": ema50,
            "ema_200": ema200,
            "macd_histogram": histogram,
            "rsi_14": rsi,
        },
    )


def _engine() -> RuntimeSignalEngine:
    return RuntimeSignalEngine(clock=lambda: NOW, stale_after=timedelta(days=1))


def test_warmup_rejection() -> None:
    with pytest.raises(InvalidFeatureSnapshotError, match="WARMUP"):
        _engine().generate(_feature(0, warmup=WarmupStatus.WARMING_UP))


def test_duplicate_snapshot_rejection() -> None:
    engine = _engine()
    feature = _feature(0)
    engine.generate(feature)
    with pytest.raises(DuplicateFeatureSnapshotError):
        engine.generate(feature)


def test_stale_snapshot_and_wrong_contract_are_rejected() -> None:
    stale_engine = RuntimeSignalEngine(clock=lambda: NOW, stale_after=timedelta(hours=1))
    with pytest.raises(StaleFeatureSnapshotError):
        stale_engine.generate(_feature(0))
    with pytest.raises(InvalidFeatureSnapshotError, match="only FeatureSnapshot"):
        _engine().generate({"symbol": "XAUUSD"})  # type: ignore[arg-type]


def test_deterministic_replay_and_uuidv7() -> None:
    inputs = (
        _feature(0),
        _feature(1, ema20=100.0, ema50=101.0, ema200=99.0, histogram=0.0, rsi=50.0),
        _feature(2, ema20=90.0, ema50=95.0, ema200=100.0, histogram=-1.0, rsi=35.0),
    )
    first = _engine().replay(inputs)
    second = _engine().replay(inputs)

    assert tuple(item.canonical_json() for item in first) == tuple(item.canonical_json() for item in second)
    assert tuple(item.replay_hash for item in first) == tuple(item.replay_hash for item in second)
    assert all(isinstance(item.signal_id, UUID) and item.signal_id.version == 7 for item in first)


def test_long_generation() -> None:
    signal = _engine().generate(_feature(0))
    assert signal.signal_type is SignalType.LONG
    assert signal.reason_codes == ("EMA_BULL_STACK", "ENTRY_TIMING", "MACD_CONFIRM", "RSI_FILTER_PASS")


def test_short_generation() -> None:
    signal = _engine().generate(
        _feature(0, ema20=90.0, ema50=95.0, ema200=100.0, histogram=-1.0, rsi=35.0)
    )
    assert signal.signal_type is SignalType.SHORT
    assert signal.reason_codes == ("EMA_BEAR_STACK", "ENTRY_TIMING", "MACD_CONFIRM", "RSI_FILTER_PASS")




def test_first_touch_only_fires_once() -> None:
    engine = _engine()
    first = engine.generate(_feature(0))
    second = engine.generate(_feature(1))
    assert first.signal_type is SignalType.LONG
    assert second.signal_type is SignalType.HOLD
    assert "ENTRY_TIMING_WAIT" in second.reason_codes


def test_exit_generation_when_active_trend_is_invalidated() -> None:
    engine = _engine()
    assert engine.generate(_feature(0)).signal_type is SignalType.LONG
    exit_signal = engine.generate(
        _feature(1, ema20=99.0, ema50=101.0, ema200=100.0, histogram=-0.1, rsi=50.0)
    )
    assert exit_signal.signal_type is SignalType.EXIT
    assert exit_signal.reason_codes == ("EXIT_CROSS",)


def test_hold_generation() -> None:
    signal = _engine().generate(
        _feature(0, ema20=101.0, ema50=100.0, ema200=99.0, histogram=-0.5, rsi=50.0)
    )
    assert signal.signal_type is SignalType.HOLD
    assert "MACD_REJECT" in signal.reason_codes
    assert "RSI_FILTER_FAIL" in signal.reason_codes


@pytest.mark.parametrize(
    "feature",
    [
        _feature(0),
        _feature(0, ema20=90.0, ema50=95.0, ema200=100.0, histogram=-1.0, rsi=35.0),
        _feature(0, ema20=100.0, ema50=100.0, ema200=100.0, histogram=0.0, rsi=50.0),
    ],
)
def test_confidence_is_finite_and_in_range(feature: FeatureSnapshot) -> None:
    confidence = _engine().generate(feature).confidence
    assert 0.0 <= confidence <= 1.0


def test_signal_snapshot_is_immutable() -> None:
    signal = _engine().generate(_feature(0))
    with pytest.raises(ValidationError):
        signal.confidence = 0.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        signal.reason_codes[0] = "CHANGED"  # type: ignore[index]


def test_canonical_replay_hash_changes_with_signal_material() -> None:
    long_signal = _engine().generate(_feature(0))
    short_signal = _engine().generate(
        _feature(0, ema20=90.0, ema50=95.0, ema200=100.0, histogram=-1.0, rsi=35.0)
    )
    replayed = _engine().generate(_feature(0))

    assert long_signal.replay_hash == replayed.replay_hash
    assert long_signal.signal_id == replayed.signal_id
    assert long_signal.replay_hash != short_signal.replay_hash
    assert len(long_signal.replay_hash) == 64


def test_strategy_version_stability_and_feature_binding() -> None:
    feature = _feature(0)
    signal = _engine().generate(feature)
    assert signal.strategy_name == STRATEGY_NAME == "forex-ema-macd-rsi-entry-timing-v1"
    assert signal.strategy_version == STRATEGY_VERSION == "1.1.0"
    assert signal.feature_digest == feature.digest


def test_feature_version_mismatch_and_missing_features_rejected() -> None:
    with pytest.raises(InvalidFeatureSnapshotError, match="version mismatch"):
        _engine().generate(_feature(0, feature_version="other-version"))

    incomplete = _feature(0).model_copy(update={"feature_values": {"ema_20": 100.0}})
    with pytest.raises(InvalidFeatureSnapshotError, match="missing required features"):
        _engine().generate(incomplete)
