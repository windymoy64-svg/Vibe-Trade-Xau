import pytest

from src.trading.precision_execution import LotSizeCalculationService


def test_calculates_and_rounds_lot_down_to_broker_step():
    result = LotSizeCalculationService().calculate(
        balance=10_000, risk_percentage=0.5, entry_price=2400, stop_loss=2395,
        tick_size=0.1, tick_value_per_lot=1,
    )

    assert result.risk_amount == 50
    assert result.stop_distance == 5
    assert result.lot_size == 1
    assert result.actual_risk_amount == 50
    assert result.bounded_by is None


def test_lot_is_bounded_and_invalid_inputs_fail_closed():
    service = LotSizeCalculationService()
    maximum = service.calculate(
        balance=100_000, risk_percentage=2, entry_price=100, stop_loss=99,
        tick_size=0.1, tick_value_per_lot=1, maximum_lot=1,
    )
    minimum = service.calculate(
        balance=100, risk_percentage=0.1, entry_price=100, stop_loss=90,
        tick_size=0.1, tick_value_per_lot=1, minimum_lot=0.01,
    )
    assert maximum.lot_size == 1 and maximum.bounded_by == "MAXIMUM_LOT"
    assert minimum.lot_size == 0.01 and minimum.bounded_by == "MINIMUM_LOT"
    with pytest.raises(ValueError, match="zero stop"):
        service.calculate(
            balance=1000, risk_percentage=1, entry_price=100, stop_loss=100,
            tick_size=0.1, tick_value_per_lot=1,
        )
