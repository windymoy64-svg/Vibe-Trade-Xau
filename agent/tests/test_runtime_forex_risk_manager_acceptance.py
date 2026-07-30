"""Acceptance tests for deterministic runtime forex risk approval."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.trading.forex_decisions import ACTION, DecisionSnapshot, PositionState, QuoteSnapshot
from src.trading.forex_risk import (
    AccountSnapshot,
    ApprovalStatus,
    ApprovedOrderPlan,
    RiskConfiguration,
    RiskPositionDirection,
    RiskPositionSnapshot,
    RuntimeForexRiskManager,
    SymbolSpecification,
)

NOW = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)


def _decision(index: int = 0) -> DecisionSnapshot:
    return DecisionSnapshot(
        decision_id=UUID("019ff5bd-6d20-7465-a13c-4a5376241e73"),
        intent_id=UUID("019ff5bd-6d20-7e1d-8fee-32d2f34d3bc0"),
        symbol="XAUUSD",
        timeframe="1h",
        broker_timestamp=NOW - timedelta(seconds=30) + timedelta(minutes=index),
        signal_id=UUID("019ff5bd-6d20-74c8-9a1c-e1709945e122"),
        signal_type="LONG",
        action=ACTION.OPEN_LONG,
        current_position_state=PositionState.FLAT,
        target_position_state=PositionState.LONG,
        reason_codes=("POSITION_FLAT", "SIGNAL_LONG"),
        replay_hash="a" * 64,
    )


def _exit_decision() -> DecisionSnapshot:
    return _decision().model_copy(update={
        "action": ACTION.CLOSE_POSITION,
        "current_position_state": PositionState.LONG,
        "target_position_state": PositionState.FLAT,
        "signal_type": "EXIT",
    })


def _position(**changes: object) -> RiskPositionSnapshot:
    payload: dict[str, object] = {
        "symbol": "XAUUSD",
        "position_ticket": 1001,
        "direction": RiskPositionDirection.LONG,
        "volume_lots": 0.37,
        "owned": True,
    }
    payload.update(changes)
    return RiskPositionSnapshot(**payload)


def _account(**changes: object) -> AccountSnapshot:
    payload: dict[str, object] = {
        "broker_timestamp": NOW - timedelta(seconds=10),
        "equity": 10_000.0,
        "free_margin": 9_000.0,
        "margin_level": 1000.0,
        "leverage": 100.0,
        "daily_loss": 0.0,
        "drawdown_percent": 0.0,
        "trades_today": 0,
        "consecutive_losses": 0,
        "symbol_exposure": 0.0,
        "correlated_exposure": 0.0,
    }
    payload.update(changes)
    return AccountSnapshot(**payload)


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


def _config(**changes: object) -> RiskConfiguration:
    payload: dict[str, object] = {
        "risk_percent": 1.0,
        "stop_loss_distance": 10.0,
        "reward_ratio": 2.0,
        "max_spread": 1.0,
        "min_free_margin": 100.0,
        "min_margin_level": 100.0,
        "max_daily_loss": 500.0,
        "max_drawdown_percent": 20.0,
        "max_trades_per_day": 10,
        "max_consecutive_losses": 3,
        "max_symbol_exposure": 100_000.0,
        "max_correlated_exposure": 200_000.0,
        "max_slippage": 0.5,
        "expiration_seconds": 60,
    }
    payload.update(changes)
    return RiskConfiguration(**payload)


def _manager() -> RuntimeForexRiskManager:
    return RuntimeForexRiskManager(clock=lambda: NOW, stale_after=timedelta(minutes=2))


def _assess_exit(**changes: object) -> ApprovedOrderPlan:
    values: dict[str, object] = {
        "decision": _exit_decision(),
        "account": _account(),
        "quote": _quote(),
        "specification": _spec(),
        "configuration": _config(),
        "position": _position(),
    }
    values.update(changes)
    return _manager().assess(**values)  # type: ignore[arg-type]


def test_close_position_is_approved_without_entry_risk_calculation() -> None:
    plan = _assess_exit(configuration=_config(risk_percent=99.0, stop_loss_distance=None))
    assert plan.approval_status is ApprovalStatus.APPROVED
    assert plan.volume_lots == pytest.approx(0.37)
    assert plan.entry_price == pytest.approx(2400.0)
    assert plan.stop_loss is None
    assert plan.take_profit is None
    assert plan.risk_percent == 0.0
    assert plan.risk_amount == 0.0


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"position": None}, "POSITION_NOT_FOUND"),
        ({"position": _position(owned=False)}, "POSITION_NOT_OWNED"),
        ({"quote": _quote(broker_timestamp=NOW - timedelta(hours=1))}, "STALE_QUOTE"),
        ({"specification": _spec(session_open=False)}, "TRADING_SESSION_CLOSED"),
        ({"specification": _spec(trading_enabled=False)}, "SYMBOL_TRADING_DISABLED"),
    ],
)
def test_close_position_fail_closed_checks(changes: dict[str, object], reason: str) -> None:
    plan = _assess_exit(**changes)
    assert plan.approval_status is ApprovalStatus.REJECTED
    assert plan.rejection_reason == reason
    assert plan.volume_lots == 0.0


def test_close_position_deterministic_replay_and_immutable_output() -> None:
    inputs = ((_exit_decision(), _account(), _quote(), _spec(), _config(), _position()),)
    first = _manager().replay(inputs)[0]
    second = _manager().replay(inputs)[0]
    assert first.canonical_json() == second.canonical_json()
    assert first.order_plan_id == second.order_plan_id
    assert first.replay_hash == second.replay_hash
    with pytest.raises(ValidationError):
        first.entry_price = 1.0  # type: ignore[misc]


def _assess(**changes: object) -> ApprovedOrderPlan:
    values = {"decision": _decision(), "account": _account(), "quote": _quote(), "specification": _spec(), "configuration": _config()}
    values.update(changes)
    return _manager().assess(**values)


def test_lot_sizing_min_max_and_step_rounding() -> None:
    approved = _assess()
    assert approved.approval_status is ApprovalStatus.APPROVED
    assert approved.volume_lots == pytest.approx(0.1)
    assert approved.entry_price == pytest.approx(2400.2)
    assert approved.stop_loss == pytest.approx(2390.2)
    assert approved.take_profit == pytest.approx(2420.2)
    assert approved.reward_ratio == 2.0
    assert approved.volume_lots >= 0.01
    assert approved.volume_lots <= 10.0
    assert _assess(configuration=_config(risk_percent=0.11)).volume_lots == pytest.approx(0.01)
    below_minimum = _assess(configuration=_config(risk_percent=0.05))
    assert below_minimum.approval_status is ApprovalStatus.REJECTED
    assert below_minimum.rejection_reason == "LOT_BELOW_MINIMUM"
    rejected = _assess(configuration=_config(risk_percent=100.0), specification=_spec(max_lot=5.0))
    assert rejected.approval_status is ApprovalStatus.REJECTED
    assert rejected.rejection_reason == "LOT_ABOVE_MAXIMUM"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"quote": _quote(spread=2.0)}, "SPREAD_LIMIT_EXCEEDED"),
        ({"quote": _quote(broker_timestamp=NOW - timedelta(hours=1))}, "STALE_QUOTE"),
        ({"account": _account(broker_timestamp=NOW - timedelta(hours=1))}, "STALE_ACCOUNT"),
        ({"configuration": _config(stop_loss_distance=None)}, "STOP_LOSS_REQUIRED"),
        ({"configuration": _config(stop_loss_distance=0.5)}, "STOP_LEVEL_VIOLATION"),
        ({"configuration": _config(stop_loss_distance=0.6), "specification": _spec(stop_level_distance=0.5, freeze_level_distance=0.75)}, "FREEZE_LEVEL_VIOLATION"),
        ({"account": _account(free_margin=50.0)}, "FREE_MARGIN_BELOW_THRESHOLD"),
        ({"account": _account(margin_level=50.0)}, "MARGIN_LEVEL_BELOW_THRESHOLD"),
        ({"account": _account(daily_loss=500.0)}, "DAILY_LOSS_LIMIT_EXCEEDED"),
        ({"account": _account(drawdown_percent=20.0)}, "MAX_DRAWDOWN_EXCEEDED"),
        ({"account": _account(symbol_exposure=100_000.0)}, "MAX_SYMBOL_EXPOSURE_EXCEEDED"),
        ({"account": _account(correlated_exposure=200_000.0)}, "CORRELATED_EXPOSURE_EXCEEDED"),
        ({"specification": _spec(trading_enabled=False)}, "SYMBOL_TRADING_DISABLED"),
        ({"specification": _spec(market_available=False)}, "MARKET_UNAVAILABLE"),
        ({"specification": _spec(session_open=False)}, "TRADING_SESSION_CLOSED"),
    ],
)
def test_fail_closed_rejections(changes: dict[str, object], reason: str) -> None:
    plan = _assess(**changes)
    assert plan.approval_status is ApprovalStatus.REJECTED
    assert plan.rejection_reason == reason
    assert plan.volume_lots == 0.0


def test_projected_margin_insufficient_and_invalid_decision() -> None:
    plan = _assess(account=_account(free_margin=200.0), specification=_spec(contract_size=1000.0))
    assert plan.rejection_reason == "PROJECTED_MARGIN_INSUFFICIENT"
    invalid = _decision().model_copy(update={"action": ACTION.HOLD})
    assert _assess(decision=invalid).rejection_reason == "ACTION_NOT_ENTRY"


def test_immutable_approved_plan_and_deterministic_replay() -> None:
    first = _assess()
    second = _assess()
    assert first.canonical_json() == second.canonical_json()
    assert first.order_plan_id == second.order_plan_id
    assert first.replay_hash == second.replay_hash
    assert first.order_plan_id.version == 7
    with pytest.raises(ValidationError):
        first.approval_status = ApprovalStatus.REJECTED  # type: ignore[misc]


def test_limits_for_trades_and_losses_and_replay_hash() -> None:
    for account, reason in [
        (_account(trades_today=10), "MAX_TRADES_PER_DAY_EXCEEDED"),
        (_account(consecutive_losses=3), "CONSECUTIVE_LOSS_LIMIT_EXCEEDED"),
    ]:
        assert _assess(account=account).rejection_reason == reason
    assert len(_assess().replay_hash) == 64
