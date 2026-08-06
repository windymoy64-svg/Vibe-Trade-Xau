from datetime import datetime, timedelta, timezone

from src.trading.auto_selection import OHLCVBar
from src.trading.precision_execution import ACRZone, evaluate_setup, is_engulfing_candle, is_rejection_candle


def _bar(index, open_, high, low, close):
    return OHLCVBar(
        datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        open_, high, low, close, 100,
    )


def _zone(formed_at):
    return ACRZone("acr-test", "BULLISH", "FRESH", formed_at, 99.0, 101.0, 102.0, 101.0, None)


def test_rejection_wick_confirms_bullish_rebound():
    bar = _bar(1, 100.0, 103.0, 98.0, 102.0)
    assert is_rejection_candle(bar, "BULLISH", 99.0, 101.0)


def test_bullish_engulfing_confirms_rebound():
    bars = (_bar(0, 102.0, 103.0, 99.5, 100.0), _bar(1, 99.8, 103.0, 99.0, 103.0))
    assert is_engulfing_candle(bars, "BULLISH")


def test_setup_expires_after_24_candles():
    bars = [_bar(0, 100, 102, 99, 101)] + [_bar(index, 101, 102, 100.5, 101) for index in range(1, 26)]
    result = evaluate_setup(_zone(bars[0].timestamp.isoformat()), bars)
    assert result.state == "EXPIRED"
    assert result.age_candles == 25


def test_setup_blocks_after_third_zone_touch():
    bars = [
        _bar(0, 100, 102, 99, 101),
        _bar(1, 101, 102, 100, 101),
        _bar(2, 101, 102, 100, 101),
        _bar(3, 101, 102, 100, 101),
    ]
    result = evaluate_setup(_zone(bars[0].timestamp.isoformat()), bars)
    assert result.state == "TOO_MANY_TOUCHES"
    assert result.touch_count == 3
