from src.trading.precision_execution import (
    ACRZone,
    FVGACRConfluenceService,
    FairValueGap,
)


def _gap(**overrides):
    return FairValueGap(**{
        "id": "fvg-1", "direction": "BULLISH", "status": "OPEN",
        "formed_at": "2026-08-01T09:00:00Z", "low": 100, "high": 104,
        "fill_percentage": 0, **overrides,
    })


def _zone(**overrides):
    return ACRZone(**{
        "id": "acr-1", "direction": "BULLISH", "status": "FRESH",
        "formed_at": "2026-08-01T08:45:00Z", "low": 102, "high": 106,
        "trigger_close": 105, "reference_boundary": 103,
        "invalidation": None, **overrides,
    })


def test_detects_and_ranks_directional_overlap():
    confluences = FVGACRConfluenceService().detect(
        [_gap(), _gap(id="fvg-2", low=103, high=105)],
        [_zone()],
    )

    assert confluences[0].fvg_id == "fvg-2"
    assert confluences[0].overlap_percentage == 100
    assert (confluences[1].overlap_low, confluences[1].overlap_high) == (102, 104)
    assert confluences[1].overlap_percentage == 50


def test_ignores_wrong_direction_inactive_and_boundary_touch():
    service = FVGACRConfluenceService()
    assert service.detect([_gap(direction="BEARISH")], [_zone()]) == ()
    assert service.detect([_gap(status="FILLED")], [_zone()]) == ()
    assert service.detect([_gap()], [_zone(status="INVALID")]) == ()
    assert service.detect([_gap(high=102)], [_zone(low=102)]) == ()
