import pytest

from src.trading.precision_execution import TradeLevelCalculationService


def test_calculates_zone_buffered_buy_sl_and_multi_tp():
    result = TradeLevelCalculationService().calculate(
        direction="BUY", entry_price=100, zone_low=95, zone_high=98,
        pip_size=0.1, stop_buffer_pips=3,
    )

    assert result.stop_loss == 94.7
    assert result.risk_distance == 5.3
    assert [target.price for target in result.targets] == [105.3, 110.6, 115.9]
    assert sum(target.allocation_percentage for target in result.targets) == 100


def test_calculates_sell_targets_and_validates_risk_contract():
    result = TradeLevelCalculationService().calculate(
        direction="SELL", entry_price=100, zone_low=102, zone_high=105,
        pip_size=0.1,
    )
    assert result.stop_loss == 105.3
    assert [target.price for target in result.targets] == [94.7, 89.4, 84.1]
    with pytest.raises(ValueError, match="total"):
        TradeLevelCalculationService().calculate(
            direction="BUY", entry_price=100, zone_low=95, zone_high=98,
            pip_size=0.1, allocations=(50, 20, 20),
        )
    with pytest.raises(ValueError, match="profitable"):
        TradeLevelCalculationService().calculate(
            direction="BUY", entry_price=90, zone_low=95, zone_high=98, pip_size=0.1,
        )
