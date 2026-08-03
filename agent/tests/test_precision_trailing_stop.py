from datetime import datetime, timezone

from src.trading.precision_execution import ACRTrailingStopService, ACRZone


def _zone(id_, formed_at, low, high, **overrides):
    return ACRZone(**{
        "id": id_, "direction": "BULLISH", "status": "FRESH",
        "formed_at": formed_at, "low": low, "high": high,
        "trigger_close": high, "reference_boundary": high - 1,
        "invalidation": None, **overrides,
    })


def test_buy_trailing_stop_moves_only_up_on_new_fresh_zones():
    result = ACRTrailingStopService().calculate(
        direction="BUY", initial_stop=90, current_price=110,
        opened_at=datetime(2026, 8, 1, 8, tzinfo=timezone.utc),
        zones=[
            _zone("old", "2026-08-01T07:00:00Z", 95, 98),
            _zone("first", "2026-08-01T09:00:00Z", 100, 103),
            _zone("lower", "2026-08-01T10:00:00Z", 98, 101),
            _zone("invalid", "2026-08-01T11:00:00Z", 105, 108, status="INVALID"),
        ],
        pip_size=0.1,
    )

    assert result.current_stop == 99.7
    assert [update.zone_id for update in result.updates] == ["first"]


def test_sell_trailing_stop_moves_down_and_rejects_stop_beyond_price():
    result = ACRTrailingStopService().calculate(
        direction="SELL", initial_stop=120, current_price=90,
        opened_at=datetime(2026, 8, 1, 8, tzinfo=timezone.utc),
        zones=[
            _zone("first", "2026-08-01T09:00:00Z", 100, 105, direction="BEARISH"),
            _zone("past", "2026-08-01T10:00:00Z", 80, 85, direction="BEARISH"),
        ],
        pip_size=0.1,
    )

    assert result.current_stop == 105.3
    assert [update.zone_id for update in result.updates] == ["first"]
