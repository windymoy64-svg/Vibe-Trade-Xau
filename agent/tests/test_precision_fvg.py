from datetime import datetime, timedelta, timezone

from src.trading.auto_selection import OHLCVBar
from src.trading.precision_execution import FairValueGapDetectionService


def _bar(index, open_, high, low, close):
    return OHLCVBar(
        datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        open_, high, low, close, 100,
    )


def test_detects_bullish_fvg_and_partial_fill():
    bars = [
        _bar(0, 100, 101, 99, 100.5),
        _bar(1, 100.5, 105, 100, 104.5),
        _bar(2, 104, 106, 103, 105),
        _bar(3, 105, 106, 102, 104),
    ]

    gap = FairValueGapDetectionService(minimum_gap=1).detect(bars)[0]

    assert gap.direction == "BULLISH"
    assert (gap.low, gap.high) == (101, 103)
    assert gap.status == "PARTIAL"
    assert gap.fill_percentage == 50


def test_detects_bearish_fvg_and_full_fill():
    bars = [
        _bar(0, 105, 106, 104, 105),
        _bar(1, 105, 105.5, 99, 100),
        _bar(2, 100, 102, 98, 99),
        _bar(3, 99, 105, 98.5, 104),
    ]

    gap = FairValueGapDetectionService().detect(bars)[0]

    assert gap.direction == "BEARISH"
    assert (gap.low, gap.high) == (102, 104)
    assert gap.status == "FILLED"
    assert gap.fill_percentage == 100
