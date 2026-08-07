from datetime import datetime, timedelta, timezone

from src.trading.auto_selection import OHLCVBar
from src.trading.precision_execution import (
    HTFMarketStructureService,
    OrderBlock,
    OrderBlockDetectionService,
    SupportResistanceDetectionService,
    confirm_area_reaction,
    detect_liquidity_sweep,
    DynamicEntryAreaSelector,
)
from src.trading.precision_execution import DynamicEntryAreaSelector


def _bar(index, open_, high, low, close):
    return OHLCVBar(
        datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(minutes=5 * index),
        open_, high, low, close, 100,
    )


def test_requires_structure_break_and_detects_bullish_order_block():
    bars = [
        _bar(0, 100, 101, 99, 100),
        _bar(1, 100, 102, 99.5, 101.5),
        _bar(2, 101.5, 101.8, 100, 100.5),
        _bar(3, 100.5, 104, 100.4, 103.8),
        _bar(4, 103.8, 104.2, 102.5, 103.5),
        _bar(5, 103.5, 104.5, 103, 104),
    ]
    structure = HTFMarketStructureService(pivot_span=1).map(bars)

    blocks = OrderBlockDetectionService().detect(bars, structure)

    bullish = [block for block in blocks if block.direction == "BULLISH"]
    assert bullish
    assert bullish[0].origin_index == 2
    assert bullish[0].structure_break_kind in {"BOS", "CHOCH"}


def test_wick_retest_does_not_invalidate_bullish_order_block():
    bars = [
        _bar(0, 100, 101, 99, 100),
        _bar(1, 100, 102, 99.5, 101.5),
        _bar(2, 101.5, 101.8, 100, 100.5),
        _bar(3, 100.5, 104, 100.4, 103.8),
        _bar(4, 103.8, 104.2, 99.8, 103.5),
        _bar(5, 103.5, 104.5, 103, 104),
    ]
    structure = HTFMarketStructureService(pivot_span=1).map(bars)

    blocks = OrderBlockDetectionService().detect(bars, structure)

    assert any(block.status != "INVALID" for block in blocks if block.direction == "BULLISH")


def test_close_through_bullish_order_block_invalidates_it():
    bars = [
        _bar(0, 100, 101, 99, 100),
        _bar(1, 100, 102, 99.5, 101.5),
        _bar(2, 101.5, 101.8, 100, 100.5),
        _bar(3, 100.5, 104, 100.4, 103.8),
        _bar(4, 103.8, 104.2, 99.5, 99.7),
        _bar(5, 99.7, 100, 98, 98.5),
    ]
    structure = HTFMarketStructureService(pivot_span=1).map(bars)

    blocks = OrderBlockDetectionService().detect(bars, structure)

    assert any(block.status == "INVALID" for block in blocks if block.direction == "BULLISH")


def test_dynamic_selector_treats_order_block_and_other_areas_as_candidates():
    block = OrderBlock(
        id="ob-bullish-test",
        direction="BULLISH",
        status="FRESH",
        origin_index=1,
        origin_timestamp="2026-08-01T00:05:00+00:00",
        displacement_index=2,
        displacement_timestamp="2026-08-01T00:10:00+00:00",
        low=100.0,
        high=102.0,
        structure_break_kind="BOS",
        broken_swing_price=103.0,
        displacement_ratio=1.5,
        mitigation_count=0,
    )

    candidates = DynamicEntryAreaSelector().select(
        current_price=101.5,
        direction="BULLISH",
        order_blocks=[block],
        acr_zones=[],
        gaps=[],
        supply_demand=[],
        support_resistance=[],
        bars=[_bar(0, 100, 101, 99, 100)],
    )

    assert candidates[0].type == "ORDER_BLOCK"
    assert candidates[0].low == 100.0


def test_detects_support_and_resistance_candidates_from_confirmed_swings():
    bars = [
        _bar(0, 100, 101, 99, 100),
        _bar(1, 100, 103, 99.8, 102.5),
        _bar(2, 102.5, 102.5, 101, 101.5),
        _bar(3, 101.5, 102, 98.5, 99),
        _bar(4, 99, 101, 98.8, 100.5),
        _bar(5, 100.5, 102.8, 100, 102.5),
        _bar(6, 103.5, 104, 102, 102.5),
    ]
    structure = HTFMarketStructureService(pivot_span=1).map(bars)

    zones = SupportResistanceDetectionService().detect(bars, structure)

    assert {zone.type for zone in zones} == {"SUPPORT", "RESISTANCE"}
    assert all(zone.status in {"ACTIVE", "INVALID"} for zone in zones)


def test_generic_area_confirmation_detects_bullish_rejection():
    bars = [
        _bar(0, 100, 101, 99, 100),
        _bar(1, 100, 102, 98.5, 101.8),
    ]

    assert confirm_area_reaction(bars, direction="BULLISH", low=99.5, high=100.5) == "REACTION_CONFIRMED"


def test_generic_area_confirmation_detects_closed_candle_liquidity_sweep():
    bars = [_bar(0, 100, 101, 99, 100), _bar(1, 100, 102, 98.5, 101.8)]

    assert detect_liquidity_sweep(bars, direction="BULLISH", low=99.5, high=100.5)
    assert not detect_liquidity_sweep(bars, direction="BEARISH", low=99.5, high=100.5)


def test_dynamic_selector_filters_far_areas_and_exposes_reaction_metadata():
    bars = [_bar(0, 100, 101, 99, 100), _bar(1, 100, 102, 98.5, 101.8)]
    block = OrderBlock(
        id="ob-near",
        direction="BULLISH",
        status="FRESH",
        origin_index=0,
        origin_timestamp=bars[0].timestamp.isoformat(),
        displacement_index=1,
        displacement_timestamp=bars[1].timestamp.isoformat(),
        low=99.5,
        high=100.5,
        structure_break_kind="BOS",
        broken_swing_price=101.0,
        displacement_ratio=1.5,
        mitigation_count=0,
    )

    candidates = DynamicEntryAreaSelector().select(
        current_price=101.8,
        direction="BULLISH",
        order_blocks=[block], acr_zones=[], gaps=[], supply_demand=[],
        support_resistance=[], bars=bars,
    )

    assert candidates[0].reaction_status == "REACTION_CONFIRMED"
    assert candidates[0].age_candles == 1
    assert candidates[0].liquidity_sweep is True
