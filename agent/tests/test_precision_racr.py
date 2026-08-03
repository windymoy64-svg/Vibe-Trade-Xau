from datetime import datetime, timedelta, timezone

import pytest

from src.trading.auto_selection import OHLCVBar
from src.trading.precision_execution import RACRReversalDetectionService


def _bar(index, open_, high, low, close):
    return OHLCVBar(
        datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        open_, high, low, close, 100,
    )


def test_detects_bullish_low_sweep_reclaim_and_bearish_high_sweep_rejection():
    bars = [
        _bar(0, 100, 102, 99, 101), _bar(1, 101, 103, 100, 102),
        _bar(2, 102, 104, 101, 103),
        _bar(3, 98.5, 102, 98, 101),
        _bar(4, 101, 103, 100, 102), _bar(5, 102, 104, 101, 103),
        _bar(6, 104.5, 105, 102, 103),
    ]

    signals = RACRReversalDetectionService(lookback=3).detect(bars)

    assert [(signal.direction, signal.sweep_price, signal.reclaimed_level) for signal in signals] == [
        ("BULLISH", 98, 99), ("BEARISH", 105, 104),
    ]


def test_equal_extreme_and_sweep_without_reclaim_do_not_trigger():
    bars = [
        _bar(0, 100, 102, 99, 101), _bar(1, 101, 103, 100, 102),
        _bar(2, 102, 104, 101, 103),
        _bar(3, 100, 104, 99, 100),
        _bar(4, 99, 101, 98, 98.5),
    ]
    assert RACRReversalDetectionService(lookback=3).detect(bars) == ()
    with pytest.raises(ValueError, match="insufficient"):
        RACRReversalDetectionService(lookback=3).detect(bars[:3])
