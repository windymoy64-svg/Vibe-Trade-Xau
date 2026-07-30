"""Acceptance tests for the injected-transport Runtime MT5 Order Executor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.trading.forex_decisions import QuoteSnapshot
from src.trading.forex_execution import (
    BrokerCheckResult,
    BrokerExecutionResponse,
    DuplicateExecutionError,
    DuplicateIntentError,
    ExecutionStatus,
    MT5TradingProfile,
    RuntimeMT5OrderExecutor,
)
from src.trading.forex_risk import ApprovalStatus, ApprovedOrderPlan, SymbolSpecification

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


class FakeTransport:
    def __init__(self, *, check=None, response=None):  # type: ignore[no-untyped-def]
        self.check = check or BrokerCheckResult(passed=True, retcode=0, comment="check ok")
        self.response = response or BrokerExecutionResponse(
            retcode=10009,
            comment="done",
            order_ticket=2001,
            deal_ticket=3001,
            position_ticket=1001,
            filled_volume=0.1,
            filled_price=2400.2,
        )
        self.check_calls = 0
        self.send_calls = 0
        self.quote_refreshes = 0
        self.symbol_refreshes = 0
        self.requests: list[dict[str, object]] = []

    def refresh_quote(self, quote, profile):  # type: ignore[no-untyped-def]
        self.quote_refreshes += 1
        return quote

    def refresh_symbol(self, specification, profile):  # type: ignore[no-untyped-def]
        self.symbol_refreshes += 1
        return specification

    def order_check(self, request, profile):  # type: ignore[no-untyped-def]
        self.check_calls += 1
        self.requests.append(request)
        return self.check

    def order_send(self, request, profile):  # type: ignore[no-untyped-def]
        self.send_calls += 1
        self.requests.append(request)
        return self.response


def _plan(action: str = "OPEN_LONG", *, index: int = 0) -> ApprovedOrderPlan:
    return ApprovedOrderPlan(
        order_plan_id=UUID(int=UUID("019ff5bd-6d20-7465-a13c-4a5376241e73").int + index),
        intent_id=UUID(int=UUID("019ff5bd-6d20-7e1d-8fee-32d2f34d3bc0").int + index),
        symbol="XAUUSD",
        action=action,
        volume_lots=0.1,
        entry_price=2400.2,
        stop_loss=2390.2,
        take_profit=2420.2,
        risk_percent=1.0,
        risk_amount=100.0,
        reward_ratio=2.0,
        max_slippage=0.5,
        expiration=NOW + timedelta(minutes=1),
        approval_status=ApprovalStatus.APPROVED,
        rejection_reason=None,
        replay_hash="a" * 64,
    )


def _spec(**changes: object) -> SymbolSpecification:
    payload: dict[str, object] = {
        "symbol": "XAUUSD",
        "tick_size": 0.01,
        "tick_value_per_lot": 1.0,
        "contract_size": 100.0,
        "lot_step": 0.01,
        "min_lot": 0.01,
        "max_lot": 10.0,
        "stop_level_distance": 1.0,
        "freeze_level_distance": 0.5,
    }
    payload.update(changes)
    return SymbolSpecification(**payload)


def _quote(**changes: object) -> QuoteSnapshot:
    payload: dict[str, object] = {
        "symbol": "XAUUSD",
        "timeframe": "1h",
        "broker_timestamp": NOW - timedelta(seconds=5),
        "bid": 2400.0,
        "ask": 2400.2,
        "spread": 0.2,
    }
    payload.update(changes)
    return QuoteSnapshot(**payload)


def _profile(**changes: object) -> MT5TradingProfile:
    payload: dict[str, object] = {
        "profile_name": "mt5-demo",
        "trade_mode": "DEMO",
        "stop_level_distance": 1.0,
        "freeze_level_distance": 0.5,
        "filling_mode": "IOC",
        "execution_mode": "MARKET",
        "expiration_policy": "GTC",
    }
    payload.update(changes)
    return MT5TradingProfile(**payload)


def _executor(transport: FakeTransport) -> RuntimeMT5OrderExecutor:
    return RuntimeMT5OrderExecutor(transport, clock=lambda: NOW)


def test_order_check_failure_never_calls_order_send() -> None:
    transport = FakeTransport(check=BrokerCheckResult(passed=False, retcode=10030, comment="invalid stops"))
    result = _executor(transport).execute(_plan(), _spec(), _quote(), _profile())
    assert result.execution_status is ExecutionStatus.REJECTED
    assert result.broker_retcode == 10030
    assert transport.check_calls == 1
    assert transport.send_calls == 0


@pytest.mark.parametrize(
    ("action", "side"),
    [("OPEN_LONG", "buy"), ("OPEN_SHORT", "sell")],
)
def test_successful_buy_and_sell(action: str, side: str) -> None:
    transport = FakeTransport()
    result = _executor(transport).execute(_plan(action), _spec(), _quote(), _profile())
    assert result.execution_status is ExecutionStatus.FILLED
    assert transport.requests[0]["side"] == side
    assert result.mt5_order_ticket == 2001
    assert result.mt5_deal_ticket == 3001
    assert transport.quote_refreshes == 1
    assert transport.symbol_refreshes == 1


@pytest.mark.parametrize(
    "action",
    ["CLOSE_POSITION", "REVERSE_TO_LONG", "REVERSE_TO_SHORT"],
)
def test_close_and_reversal_actions(action: str) -> None:
    transport = FakeTransport()
    close_metadata = (1001, "LONG") if action == "CLOSE_POSITION" else ()
    result = _executor(transport).execute(
        _plan(action), _spec(), _quote(), _profile(), *close_metadata
    )
    assert result.execution_status is ExecutionStatus.FILLED
    assert transport.requests[0]["action"] == action


def test_close_position_rejects_missing_position_ticket() -> None:
    transport = FakeTransport()
    with pytest.raises(ValueError, match="position ticket missing"):
        _executor(transport).execute(
            _plan("CLOSE_POSITION"), _spec(), _quote(), _profile(), position_side="LONG"
        )
    assert transport.check_calls == 0
    assert transport.send_calls == 0


def test_close_position_rejects_missing_position_side() -> None:
    transport = FakeTransport()
    with pytest.raises(ValueError, match="position side missing"):
        _executor(transport).execute(
            _plan("CLOSE_POSITION"), _spec(), _quote(), _profile(), position_ticket=1001
        )
    assert transport.check_calls == 0
    assert transport.send_calls == 0


def test_partial_fill_rejected_and_unknown_results() -> None:
    partial = FakeTransport(response=BrokerExecutionResponse(
        retcode=10010, comment="partial", order_ticket=2001, deal_ticket=3001,
        position_ticket=1001, filled_volume=0.04, filled_price=2400.2,
    ))
    assert _executor(partial).execute(_plan(), _spec(), _quote(), _profile()).execution_status is ExecutionStatus.PARTIALLY_FILLED
    rejected = FakeTransport(response=BrokerExecutionResponse(retcode=10016, comment="rejected"))
    assert _executor(rejected).execute(_plan(), _spec(), _quote(), _profile()).execution_status is ExecutionStatus.REJECTED
    unknown = FakeTransport(response=BrokerExecutionResponse(retcode=None, comment="connection lost"))
    result = _executor(unknown).execute(_plan(), _spec(), _quote(), _profile())
    assert result.execution_status is ExecutionStatus.UNKNOWN
    assert unknown.send_calls == 1


def test_duplicate_intent_and_order_plan_rejection() -> None:
    executor = _executor(FakeTransport())
    executor.execute(_plan(), _spec(), _quote(), _profile())
    with pytest.raises(DuplicateIntentError):
        executor.execute(_plan(), _spec(), _quote(), _profile())
    executor2 = _executor(FakeTransport())
    executor2._seen_plans.add(_plan().order_plan_id)  # acceptance seam for independent plan invariant
    with pytest.raises(DuplicateExecutionError):
        executor2.execute(_plan(), _spec(), _quote(), _profile())


def test_fail_closed_metadata_quote_and_action_validation() -> None:
    cases = [
        (_plan("HOLD"), _spec(), _quote(), _profile()),
        (_plan(), _spec(trading_enabled=False), _quote(), _profile()),
        (_plan(), _spec(), _quote(broker_timestamp=NOW - timedelta(hours=1)), _profile()),
        (_plan(), _spec(stop_level_distance=20.0), _quote(), _profile()),
        (_plan(), _spec(), _quote(), _profile(session_open=False)),
    ]
    for args in cases:
        with pytest.raises(ValueError):
            _executor(FakeTransport()).execute(*args)


def test_immutable_deterministic_replay_hash_and_uuidv7() -> None:
    first = _executor(FakeTransport()).execute(_plan(), _spec(), _quote(), _profile())
    second = _executor(FakeTransport()).execute(_plan(), _spec(), _quote(), _profile())
    assert first.canonical_json() == second.canonical_json()
    assert first.execution_id.version == 7
    assert first.replay_hash == second.replay_hash
    assert len(first.replay_hash) == 64
    with pytest.raises(ValidationError):
        first.execution_status = ExecutionStatus.REJECTED  # type: ignore[misc]
