import math

import pytest

from src.trading.auto_trade import (
    TradingParameterLimits,
    TradingParameters,
    TradingParameterValidationService,
)


def _parameters(**overrides):
    return TradingParameters(**{
        "symbol": " xauusd ", "timeframe": "m15", "side": "BUY",
        "lot_size": 0.057, "entry_price": 2389.8, "stop_loss": 2383.8,
        "take_profit": 2401.8, **overrides,
    })


def test_parameters_are_normalized_conservatively():
    result = TradingParameterValidationService().validate(_parameters())

    assert result.symbol == "XAUUSD"
    assert result.timeframe == "M15"
    assert result.lot_size == 0.05


def test_side_specific_price_geometry_is_required():
    service = TradingParameterValidationService()

    with pytest.raises(ValueError, match="BUY"):
        service.validate(_parameters(stop_loss=2390))
    sell = service.validate(_parameters(
        side="SELL", stop_loss=2395, take_profit=2380,
    ))
    assert sell.side == "SELL"
    with pytest.raises(ValueError, match="SELL"):
        service.validate(_parameters(side="SELL"))


def test_invalid_symbols_limits_and_non_finite_values_fail_closed():
    service = TradingParameterValidationService()

    with pytest.raises(ValueError, match="symbol"):
        service.validate(_parameters(symbol="XAU/USD;DROP"))
    with pytest.raises(ValueError, match="timeframe"):
        service.validate(_parameters(timeframe="H2"))
    with pytest.raises(ValueError, match="finite"):
        service.validate(_parameters(entry_price=math.inf))
    with pytest.raises(ValueError, match="outside"):
        service.validate(_parameters(lot_size=1.1), TradingParameterLimits(maximum_lot=1))
