from datetime import datetime, timedelta, timezone

import pytest

from src.trading.auto_selection import OHLCVBar
from src.trading.precision_execution import HTFMarketStructureService


def _bars(closes):
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    return tuple(
        OHLCVBar(start + timedelta(hours=index), close, close + 1, close - 1, close, 100)
        for index, close in enumerate(closes)
    )


def test_structure_maps_confirmed_swings_bos_and_choch_once():
    bars = _bars([10, 12, 15, 12, 10, 17, 14, 11, 8, 12, 16])

    result = HTFMarketStructureService(pivot_span=1).map(bars)

    assert [(swing.kind, swing.index, swing.price) for swing in result.swings] == [
        ("HIGH", 2, 16), ("LOW", 4, 9), ("HIGH", 5, 18), ("LOW", 8, 7),
    ]
    assert [(event.kind, event.direction, event.index) for event in result.breaks] == [
        ("BOS", "BULLISH", 5), ("CHOCH", "BEARISH", 8),
    ]
    assert result.bias == "BEARISH"


def test_structure_requires_enough_candles_and_strict_pivots():
    with pytest.raises(ValueError, match="insufficient"):
        HTFMarketStructureService(pivot_span=2).map(_bars([1, 2, 3, 4]))
    result = HTFMarketStructureService(pivot_span=1).map(_bars([10, 10, 10, 10, 10]))
    assert result.swings == ()
    assert result.breaks == ()
