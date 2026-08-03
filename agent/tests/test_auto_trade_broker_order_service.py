import pytest

from src.trading.auto_trade import (
    BrokerOrderRequest,
    BrokerOrderService,
    DuplicateBrokerOrderError,
)


def _request(**overrides):
    return BrokerOrderRequest(**{
        "idempotency_key": "signal-1", "profile_id": "mt5-paper",
        "symbol": "xauusd", "side": "buy", "quantity": 0.05,
        "session_id": "session-1", **overrides,
    })


def test_order_is_submitted_once_through_protected_service_contract():
    calls = []

    def submitter(*args, **kwargs):
        calls.append((args, kwargs))
        return {"status": "ok", "order_id": 1842, "filled_price": 2389.8}

    service = BrokerOrderService(submitter)
    result = service.submit(_request())

    assert result.status == "ACCEPTED"
    assert result.broker_order_id == "1842"
    assert calls == [(('XAUUSD', 'mt5-paper'), {
        "side": "buy", "quantity": 0.05, "order_type": "market",
        "limit_price": None, "time_in_force": "day", "session_id": "session-1",
    })]
    assert "api_key" not in calls[0][1]
    with pytest.raises(DuplicateBrokerOrderError):
        service.submit(_request())
    assert len(calls) == 1


def test_broker_rejection_and_transport_error_are_normalized():
    rejected = BrokerOrderService(
        lambda *args, **kwargs: {"status": "error", "error": "market closed"},
    ).submit(_request())
    failed = BrokerOrderService(
        lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("broker timeout")),
    ).submit(_request(idempotency_key="signal-2"))

    assert rejected.status == "REJECTED"
    assert rejected.message == "market closed"
    assert failed.status == "ERROR"
    assert failed.message == "broker timeout"


def test_order_request_requires_safe_sizing_and_limit_price():
    with pytest.raises(ValueError):
        _request(quantity=0)
    with pytest.raises(ValueError):
        _request(order_type="limit")
