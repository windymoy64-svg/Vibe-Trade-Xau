from datetime import datetime, timedelta, timezone

from src.trading.auto_selection import OHLCVBar
from src.trading.precision_execution import LTFSupplyDemandService


def _bar(index, open_, high, low, close):
    return OHLCVBar(
        datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=15 * index),
        open_, high, low, close, 100,
    )


def test_detects_demand_zone_and_tracks_retest():
    bars = [
        _bar(0, 100, 101, 99, 100.5), _bar(1, 100.5, 101.5, 100, 101),
        _bar(2, 101, 102, 100.5, 101.5), _bar(3, 101.5, 102, 100.5, 101),
        _bar(4, 101, 101.5, 100, 100.5),
        _bar(5, 100.5, 101, 99.5, 100),
        _bar(6, 100, 104.5, 99.8, 104),
        _bar(7, 104, 105, 102, 103),
        _bar(8, 103, 104, 100.3, 102),
    ]

    zones = LTFSupplyDemandService(lookback=5).detect(bars)

    assert len(zones) == 1
    assert zones[0].type == "DEMAND"
    assert (zones[0].low, zones[0].high) == (99.5, 100.5)
    assert zones[0].status == "TESTED"


def test_detects_supply_zone_and_marks_close_invalidation():
    bars = [
        _bar(0, 100, 101, 99, 100), _bar(1, 100, 101, 99, 100),
        _bar(2, 100, 101, 99, 100), _bar(3, 100, 101, 99, 100),
        _bar(4, 100, 101, 99, 100),
        _bar(5, 100, 101.5, 99.8, 101),
        _bar(6, 101, 101.2, 96, 96.5),
        _bar(7, 96.5, 100, 96, 99),
        _bar(8, 99, 102, 98, 101.6),
    ]

    zone = LTFSupplyDemandService(lookback=5).detect(bars)[0]

    assert zone.type == "SUPPLY"
    assert (zone.low, zone.high) == (100, 101.5)
    assert zone.status == "INVALID"
