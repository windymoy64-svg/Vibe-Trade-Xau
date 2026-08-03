from datetime import datetime, timedelta, timezone

from src.trading.auto_selection import OHLCVBar
from src.trading.precision_execution import (
    ACRZoneDetectionService,
    ACRZoneStatusValidationService,
)


def _bar(index, open_, high, low, close):
    return OHLCVBar(
        datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        open_, high, low, close, 100,
    )


def test_detects_fresh_bullish_close_break_zone():
    bars = [
        _bar(0, 100, 102, 99, 101),
        _bar(1, 101, 104, 100.5, 103),
        _bar(2, 103, 105, 100, 104),
    ]

    zones = ACRZoneDetectionService().detect(bars)

    assert len(zones) == 1
    assert zones[0].direction == "BULLISH"
    assert (zones[0].low, zones[0].high) == (99, 104)
    assert zones[0].reference_boundary == 102
    assert zones[0].status == "FRESH"


def test_bearish_zone_requires_close_break_and_tracks_close_invalidation():
    bars = [
        _bar(0, 103, 104, 101, 102),
        _bar(1, 102, 103, 98, 99),
        _bar(2, 99, 103.5, 98.5, 102),
        _bar(3, 102, 105, 101, 104.5),
    ]

    zones = ACRZoneDetectionService().detect(bars)

    assert zones[0].direction == "BEARISH"
    assert zones[0].status == "INVALID"
    assert zones[0].invalidation is not None
    assert zones[0].invalidation.close == 104.5


def test_zone_status_validation_is_incremental_and_monotonic():
    original = ACRZoneDetectionService().detect([
        _bar(0, 100, 102, 99, 101),
        _bar(1, 101, 104, 100.5, 103),
    ])[0]
    service = ACRZoneStatusValidationService()

    fresh = service.validate(original, [_bar(2, 103, 105, 99.2, 102)])
    invalid = service.validate(fresh, [_bar(3, 102, 103, 97, 98)])
    unchanged = service.validate(invalid, [_bar(4, 98, 105, 97, 104)])

    assert fresh.status == "FRESH"
    assert invalid.status == "INVALID"
    assert invalid.invalidation is not None and invalid.invalidation.close == 98
    assert unchanged is invalid
