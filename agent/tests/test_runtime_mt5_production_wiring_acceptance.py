"""Acceptance tests for injected production MT5 runtime wiring."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from src.trading.forex_execution import MT5TradingProfile
from src.trading.forex_risk import SymbolSpecification
from src.trading.runtime_pipeline import MT5BrokerTransport, MT5RuntimeInputs

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


class FakeMT5:
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_FILLING_IOC = 1

    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def symbol_info(self, symbol):  # type: ignore[no-untyped-def]
        return SimpleNamespace(trade_allowed=True, trade_tick_size=.01, trade_contract_size=100,
                               volume_step=.01, volume_min=.01, volume_max=10,
                               trade_stops_level=1, trade_freeze_level=.5)

    def symbol_info_tick(self, symbol):  # type: ignore[no-untyped-def]
        return SimpleNamespace(bid=2400.0, ask=2400.2, spread=.2, time=int(NOW.timestamp()))

    def account_info(self):  # type: ignore[no-untyped-def]
        return SimpleNamespace(time=int(NOW.timestamp()), equity=10000, margin_free=9000,
                               margin_level=1000, leverage=100)

    def order_check(self, request):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        return SimpleNamespace(retcode=0, comment="ok")

    def order_send(self, request):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        return SimpleNamespace(retcode=10009, comment="done", order=2001, deal=3001,
                               position=1001, volume=.1, price=2400.2)

    def positions_get(self, **kwargs):  # type: ignore[no-untyped-def]
        return (SimpleNamespace(ticket=1001, type=0, volume=.1, price_open=2400.2,
                                sl=2390.2, tp=2420.2, time=int(NOW.timestamp()),
                                magic=862001, comment="vibe-trading"),)

    def orders_get(self, **kwargs):  # type: ignore[no-untyped-def]
        return ()

    def history_deals_get(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return ()


def _profile() -> MT5TradingProfile:
    return MT5TradingProfile(profile_name="demo", trade_mode="demo", stop_level_distance=1,
                             freeze_level_distance=.5, filling_mode="IOC", execution_mode="MARKET",
                             expiration_policy="GTC")


def _spec() -> SymbolSpecification:
    return SymbolSpecification(symbol="XAUUSD", tick_size=.01, tick_value_per_lot=1,
        contract_size=100, lot_step=.01, min_lot=.01, max_lot=10,
        stop_level_distance=1, freeze_level_distance=.5)


@pytest.mark.parametrize("action,side", [
    ("OPEN_LONG", "buy"), ("OPEN_SHORT", "sell"),
    ("REVERSE_TO_LONG", "buy"), ("REVERSE_TO_SHORT", "sell"),
])
def test_entry_and_reversal_requests_translate_to_mt5(action: str, side: str) -> None:
    api = FakeMT5()
    transport = MT5BrokerTransport(api, clock=lambda: NOW)
    request = {"symbol": "XAUUSD", "action": action, "side": side, "volume": .1,
               "price": 2400.2, "stop_loss": 2390.2, "take_profit": 2420.2,
               "deviation": .5, "filling_mode": "IOC"}
    assert transport.order_check(request, _profile()).passed
    translated = api.requests[0]
    assert translated["type"] == (0 if side == "buy" else 1)
    assert translated["type_filling"] == api.ORDER_FILLING_IOC
    assert translated["sl"] == 2390.2 and translated["tp"] == 2420.2


def test_close_is_ticket_pinned_and_runtime_inputs_refresh_all_evidence() -> None:
    api = FakeMT5()
    transport = MT5BrokerTransport(api, clock=lambda: NOW)
    request = {"symbol": "XAUUSD", "action": "CLOSE_POSITION", "side": "sell",
               "volume": .1, "price": 2400.0, "position": 1001,
               "deviation": .5, "filling_mode": "IOC"}
    response = transport.order_send(request, _profile())
    assert response.retcode == 10009 and api.requests[0]["position"] == 1001
    assert "sl" not in api.requests[0] and "tp" not in api.requests[0]

    inputs = MT5RuntimeInputs(api, specification=_spec(), profile=_profile(), clock=lambda: NOW)
    account, quote, specification = inputs.risk_inputs({})
    assert account.equity == 10000 and quote.bid == 2400 and specification.symbol == "XAUUSD"
    assert inputs.current_position({}).position_ticket == 1001  # type: ignore[union-attr]
    positions, orders, deals = inputs.position_evidence({})
    assert positions.positions[0].ticket == 1001 and orders.orders == () and deals.deals == ()


def test_missing_order_check_result_fails_closed() -> None:
    api = FakeMT5()
    api.order_check = lambda request: None  # type: ignore[method-assign]
    result = MT5BrokerTransport(api).order_check(
        {"symbol": "XAUUSD", "side": "buy", "volume": .1, "price": 2400.2,
         "deviation": .5, "filling_mode": "IOC"}, _profile()
    )
    assert not result.passed
