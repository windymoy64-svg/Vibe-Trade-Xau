import math

import pytest

from src.trading.precision_execution import FibonacciPremiumDiscountService


def test_buy_discount_and_sell_premium_are_eligible():
    service = FibonacciPremiumDiscountService()
    buy = service.calculate(
        swing_low=2300, swing_high=2400, current_price=2360,
        setup_zone_midpoint=2340, setup_direction="BUY",
    )
    sell = service.calculate(
        swing_low=2300, swing_high=2400, current_price=2360,
        setup_zone_midpoint=2380, setup_direction="SELL",
    )

    assert buy.equilibrium == 2350
    assert buy.setup_valuation == "DISCOUNT" and buy.eligible is True
    assert sell.setup_valuation == "PREMIUM" and sell.eligible is True
    assert dict(buy.levels) == {
        "23.6%": 2323.6, "38.2%": 2338.2, "50.0%": 2350,
        "61.8%": 2361.8, "78.6%": 2378.6,
    }


def test_wrong_valuation_is_ineligible_and_inputs_are_validated():
    service = FibonacciPremiumDiscountService()
    result = service.calculate(
        swing_low=2300, swing_high=2400, current_price=2360,
        setup_zone_midpoint=2380, setup_direction="BUY",
    )
    assert result.eligible is False
    with pytest.raises(ValueError, match="below"):
        service.calculate(
            swing_low=2400, swing_high=2300, current_price=2350,
            setup_zone_midpoint=2350, setup_direction="BUY",
        )
    with pytest.raises(ValueError, match="finite"):
        service.calculate(
            swing_low=2300, swing_high=2400, current_price=math.nan,
            setup_zone_midpoint=2350, setup_direction="BUY",
        )
