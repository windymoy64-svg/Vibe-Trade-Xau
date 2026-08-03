from datetime import datetime, timedelta, timezone

import pytest

from src.trading.auto_selection import OHLCVBar, RealtimeMarketIndicatorService


def _bar(index: int, close: float, *, volume: float = 100.0) -> OHLCVBar:
    return OHLCVBar(
        timestamp=datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        open=close - 0.5,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=volume,
    )


def _service(**overrides) -> RealtimeMarketIndicatorService:
    config = {
        "fast_ema_period": 3,
        "slow_ema_period": 5,
        "rsi_period": 3,
        "atr_period": 3,
        "volume_period": 3,
        "max_bars": 20,
        **overrides,
    }
    return RealtimeMarketIndicatorService("xauusd", "m15", **config)


def test_incremental_snapshot_becomes_ready_and_classifies_bullish_trend():
    snapshot = _service().extend([_bar(index, 2000 + index * 2) for index in range(8)])

    assert snapshot.symbol == "XAUUSD"
    assert snapshot.timeframe == "M15"
    assert snapshot.ready is True
    assert snapshot.ema_fast > snapshot.ema_slow
    assert snapshot.rsi == 100
    assert snapshot.atr == 3
    assert snapshot.volume_ratio == 1
    assert snapshot.trend == "BULLISH"
    assert snapshot.volatility == "NORMAL"
    assert snapshot.regime == "TRENDING"


def test_flat_market_is_neutral_ranging_and_has_finite_rsi():
    snapshot = _service().extend([_bar(index, 2000) for index in range(8)])

    assert snapshot.rsi == 50
    assert snapshot.trend == "NEUTRAL"
    assert snapshot.regime == "RANGING"


def test_latest_live_candle_can_be_replaced_but_history_cannot_move_backwards():
    service = _service()
    bars = [_bar(index, 2000 + index) for index in range(6)]
    first = service.extend(bars)
    replacement = OHLCVBar(
        timestamp=bars[-1].timestamp,
        open=2004.5,
        high=2011,
        low=2004,
        close=2010,
        volume=150,
    )

    replaced = service.update(replacement)

    assert replaced.bar_count == first.bar_count
    assert replaced.close == 2010
    assert replaced.volume_ratio > first.volume_ratio
    with pytest.raises(ValueError, match="must not move backwards"):
        service.update(bars[-2])


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"timestamp": datetime(2026, 8, 1), "open": 1, "high": 2, "low": 0, "close": 1}, "timezone-aware"),
        ({"timestamp": datetime(2026, 8, 1, tzinfo=timezone.utc), "open": 1, "high": 0, "low": 0, "close": 1}, "high must contain"),
    ],
)
def test_bar_validation_rejects_ambiguous_market_data(kwargs, message):
    with pytest.raises(ValueError, match=message):
        OHLCVBar(**kwargs)
