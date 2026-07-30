from datetime import datetime, timedelta, timezone

import pytest

from src.trading.forex_features import RuntimeFeatureBuilder
from src.trading.runtime_config import RuntimeConfig, load_runtime_config


def _bars(count=30):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "validated": True,
            "closed": True,
            "symbol": "XAUUSD",
            "timeframe": "1h",
            "broker_timestamp": start + timedelta(hours=index),
            "open": 2000 + index,
            "high": 2002 + index,
            "low": 1998 + index,
            "close": 2000 + index + (index % 3),
            "volume": 100 + index,
            "spread": 0,
            "tick_metadata": {"source": "test"},
        }
        for index in range(count)
    ]


def test_default_config_preserves_legacy_feature_parameters():
    config = RuntimeConfig()
    builder = RuntimeFeatureBuilder(
        runtime_config=config, clock=lambda: _bars()[-1]["broker_timestamp"], stale_after=timedelta(days=365)
    )
    assert builder.parameters.model_dump() == {
        "ema_fast": 20,
        "ema_medium": 50,
        "ema_slow": 200,
        "atr_period": 14,
        "rsi_period": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "volume_sma_period": 20,
    }


def test_ema_fast_changes_behavior_without_source_change():
    bars = _bars()

    def now():
        return bars[-1]["broker_timestamp"]

    default = RuntimeFeatureBuilder(runtime_config=RuntimeConfig(), clock=now, stale_after=timedelta(days=365))
    changed = RuntimeFeatureBuilder(
        runtime_config=RuntimeConfig(EMA_FAST=15), clock=now, stale_after=timedelta(days=365)
    )
    default_output = [default.build(bar) for bar in bars][-1]
    changed_output = [changed.build(bar) for bar in bars][-1]
    assert "ema_20" in default_output.feature_values
    assert "ema_15" in changed_output.feature_values
    assert default_output.parameter_fingerprint != changed_output.parameter_fingerprint


def test_loader_is_strict_and_config_is_immutable(tmp_path):
    path = tmp_path / "runtime.yaml"
    path.write_text("EMA_FAST: 15\n", encoding="utf-8")
    config = load_runtime_config(path)
    assert config.ema_fast == 15
    with pytest.raises(Exception):
        config.ema_fast = 10
