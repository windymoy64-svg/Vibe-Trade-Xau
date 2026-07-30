"""Acceptance tests for end-to-end runtime forex orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest

from src.trading.forex_decisions import (
    ACTION, DecisionSnapshot, PendingOrdersState, PositionState,
    PositionStateSnapshot as DecisionPosition, QuoteSnapshot, StrategyRuntimeState,
)
from src.trading.forex_execution import ExecutionResult, ExecutionStatus, MT5TradingProfile
from src.trading.forex_features import FeatureParameters, FeatureSnapshot, WarmupStatus
from src.trading.forex_positions import (
    DealHistorySnapshot, Direction, MT5PositionSnapshot, PendingOrdersSnapshot,
    PositionLifecycle, PositionStateSnapshot,
)
from src.trading.forex_risk import (
    AccountSnapshot, ApprovalStatus, ApprovedOrderPlan, RiskConfiguration, SymbolSpecification,
)
from src.trading.forex_signals import SignalSnapshot, SignalType
from src.trading.runtime_pipeline import CandleOutcome, PipelineStage, RuntimeEventLog, RuntimePipelineRunner

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
U1 = UUID("019ff5bd-6d20-7465-a13c-4a5376241e73")
U2 = UUID("019ff5bd-6d20-7e1d-8fee-32d2f34d3bc0")


def _market(index: int = 0) -> dict[str, object]:
    return {
        "symbol": "XAUUSD", "timeframe": "1h", "broker_timestamp": NOW + timedelta(hours=index),
        "validated": True, "closed": True, "ohlcv": {"open": 2399.0, "high": 2401.0,
        "low": 2398.0, "close": 2400.0, "volume": 1000.0}, "spread": 0.2,
        "tick_metadata": {"bid": 2399.9, "ask": 2400.1},
    }


def _feature(status: WarmupStatus = WarmupStatus.READY) -> FeatureSnapshot:
    return FeatureSnapshot(
        symbol="XAUUSD", timeframe="1h", broker_timestamp=NOW,
        parameter_fingerprint=FeatureParameters().fingerprint, warmup_status=status,
        warmup_bars_seen=200 if status is WarmupStatus.READY else 1, warmup_bars_required=200,
        feature_values={"ema_20": 110, "ema_50": 105, "ema_200": 100,
                        "macd_histogram": 1, "rsi_14": 65},
    )


def _signal(kind: SignalType) -> SignalSnapshot:
    return SignalSnapshot(
        signal_id=U1, symbol="XAUUSD", timeframe="1h", broker_timestamp=NOW,
        strategy_name="forex-ema-macd-rsi-baseline", strategy_version="1.0.0",
        feature_digest=_feature().digest, signal_type=kind, confidence=0.8,
        reason_codes=(f"SIGNAL_{kind.value}",), replay_hash="a" * 64,
    )


def _decision(action: ACTION) -> DecisionSnapshot:
    target = PositionState.FLAT if action is ACTION.CLOSE_POSITION else (
        PositionState.SHORT if action is ACTION.OPEN_SHORT else PositionState.LONG
    )
    return DecisionSnapshot(
        decision_id=U1, intent_id=U2, symbol="XAUUSD", timeframe="1h", broker_timestamp=NOW,
        signal_id=U1, signal_type="SHORT" if action is ACTION.OPEN_SHORT else "LONG",
        action=action, current_position_state=PositionState.FLAT,
        target_position_state=target, reason_codes=("TEST",), replay_hash="b" * 64,
    )


def _plan(status: ApprovalStatus = ApprovalStatus.APPROVED, action: str = "OPEN_LONG") -> ApprovedOrderPlan:
    return ApprovedOrderPlan(
        order_plan_id=U1, intent_id=U2, symbol="XAUUSD", action=action,
        volume_lots=0.1 if status is ApprovalStatus.APPROVED else 0,
        entry_price=2400.2, stop_loss=2390.2, take_profit=2420.2,
        risk_percent=1, risk_amount=100, reward_ratio=2, max_slippage=0.5,
        expiration=NOW + timedelta(minutes=1), approval_status=status,
        rejection_reason=None if status is ApprovalStatus.APPROVED else "LIMIT",
        replay_hash="c" * 64,
    )


def _execution(status: ExecutionStatus) -> ExecutionResult:
    filled = 0.04 if status is ExecutionStatus.PARTIALLY_FILLED else (0.1 if status is ExecutionStatus.FILLED else 0)
    return ExecutionResult(
        execution_id=U1, order_plan_id=U1, intent_id=U2, symbol="XAUUSD", action="OPEN_LONG",
        execution_status=status, mt5_order_ticket=2001, mt5_deal_ticket=3001,
        mt5_position_ticket=1001, broker_retcode=None if status is ExecutionStatus.UNKNOWN else 10009,
        broker_comment=status.value, filled_volume=filled, filled_price=2400.2 if filled else None,
        execution_time=NOW, replay_hash="d" * 64,
    )


def _position(lifecycle: PositionLifecycle = PositionLifecycle.OPEN) -> PositionStateSnapshot:
    return PositionStateSnapshot(
        position_state_id=U1, strategy_position_id=U2, symbol="XAUUSD",
        strategy_name="forex-ema-macd-rsi-baseline", strategy_version="1.0.0",
        magic_number=1, comment="test", mt5_position_ticket=1001, mt5_order_ticket=2001,
        mt5_deal_ticket=3001, current_state=lifecycle, direction=Direction.LONG,
        volume_lots=0.1, entry_price=2400.2, stop_loss=2390.2, take_profit=2420.2,
        open_time=NOW, last_update_time=NOW, replay_hash="e" * 64,
    )


def _runtime_inputs(position: PositionStateSnapshot | None = None) -> Mock:
    quote = QuoteSnapshot(symbol="XAUUSD", timeframe="1h", broker_timestamp=NOW, bid=2400, ask=2400.2, spread=0.2)
    spec = SymbolSpecification(symbol="XAUUSD", tick_size=.01, tick_value_per_lot=1, contract_size=100,
        lot_step=.01, min_lot=.01, max_lot=10, stop_level_distance=1, freeze_level_distance=.5)
    account = AccountSnapshot(broker_timestamp=NOW, equity=10000, free_margin=9000, margin_level=1000,
        leverage=100, daily_loss=0, drawdown_percent=0, trades_today=0, consecutive_losses=0,
        symbol_exposure=0, correlated_exposure=0)
    runtime = Mock()
    runtime.decision_inputs.return_value = (
        DecisionPosition(symbol="XAUUSD", state=PositionState.FLAT), PendingOrdersState(symbol="XAUUSD"),
        quote, StrategyRuntimeState(),
    )
    runtime.risk_inputs.return_value = (account, quote, spec)
    runtime.execution_profile.return_value = MT5TradingProfile(profile_name="demo", trade_mode="demo",
        stop_level_distance=1, freeze_level_distance=.5, filling_mode="IOC", execution_mode="MARKET",
        expiration_policy="GTC")
    runtime.position_evidence.return_value = (
        MT5PositionSnapshot(captured_at=NOW), PendingOrdersSnapshot(captured_at=NOW),
        DealHistorySnapshot(captured_at=NOW),
    )
    runtime.update_position_state.return_value = position or _position()
    return runtime


def _runner(tmp_path: Path, *, signal=SignalType.LONG, approval=ApprovalStatus.APPROVED,
            execution=ExecutionStatus.FILLED, warmup=WarmupStatus.READY, log_name="events.jsonl"):
    feature_builder, signal_engine, decision_engine = Mock(), Mock(), Mock()
    risk_manager, executor, position_manager = Mock(), Mock(), Mock()
    feature_builder.build.return_value = _feature(warmup)
    signal_engine.generate.return_value = _signal(signal)
    action = ACTION.OPEN_SHORT if signal is SignalType.SHORT else ACTION.CLOSE_POSITION if signal is SignalType.EXIT else ACTION.OPEN_LONG
    decision_engine.decide.return_value = _decision(action)
    risk_manager.assess.return_value = _plan(approval, action.value)
    executor.execute.return_value = _execution(execution)
    position_manager.reconcile.return_value = _position(
        PositionLifecycle.PARTIALLY_FILLED if execution is ExecutionStatus.PARTIALLY_FILLED else
        PositionLifecycle.REJECTED if execution in {ExecutionStatus.REJECTED, ExecutionStatus.UNKNOWN} else PositionLifecycle.OPEN
    )
    market_data, runtime = Mock(), _runtime_inputs()
    runner = RuntimePipelineRunner(
        market_data=market_data, feature_builder=feature_builder, signal_engine=signal_engine,
        decision_engine=decision_engine, risk_manager=risk_manager, executor=executor,
        position_manager=position_manager, runtime_inputs=runtime,
        event_log=RuntimeEventLog(tmp_path / log_name), risk_configuration=Mock(), clock=lambda: NOW,
    )
    return runner, (feature_builder, signal_engine, decision_engine, risk_manager, executor, position_manager, runtime, market_data)


def test_subscribe_and_hold_path_update_position_only(tmp_path: Path) -> None:
    runner, parts = _runner(tmp_path, signal=SignalType.HOLD)
    runner.subscribe()
    parts[7].subscribe.assert_called_once_with(runner.process_candle)
    result = runner.process_candle(_market())
    assert result.outcome is CandleOutcome.HOLD
    assert [event.stage for event in result.events] == [PipelineStage.MARKET, PipelineStage.FEATURE, PipelineStage.SIGNAL, PipelineStage.POSITION]
    parts[2].decide.assert_not_called(); parts[3].assess.assert_not_called(); parts[4].execute.assert_not_called()
    parts[6].update_position_state.assert_called_once()


@pytest.mark.parametrize("signal", [SignalType.LONG, SignalType.SHORT])
def test_long_and_short_complete_full_chain(tmp_path: Path, signal: SignalType) -> None:
    runner, parts = _runner(tmp_path, signal=signal)
    result = runner.process_candle(_market())
    assert result.outcome is CandleOutcome.COMPLETED
    assert [event.stage for event in result.events] == list(PipelineStage)[:7]
    parts[6].forward_execution.assert_called_once_with(result.execution_result)
    parts[5].reconcile.assert_called_once()


def test_exit_flows_to_risk_and_stops_on_existing_risk_rejection(tmp_path: Path) -> None:
    runner, parts = _runner(tmp_path, signal=SignalType.EXIT, approval=ApprovalStatus.REJECTED)
    result = runner.process_candle(_market())
    assert result.decision_snapshot.action is ACTION.CLOSE_POSITION
    assert result.outcome is CandleOutcome.RISK_REJECTED
    parts[4].execute.assert_not_called()


def test_warmup_duplicate_and_fail_closed(tmp_path: Path) -> None:
    runner, parts = _runner(tmp_path, warmup=WarmupStatus.WARMING_UP)
    assert runner.process_candle(_market()).outcome is CandleOutcome.WARMING_UP
    assert runner.process_candle(_market()).outcome is CandleOutcome.DUPLICATE
    parts[1].generate.assert_not_called()
    failed, failed_parts = _runner(tmp_path, log_name="failed.jsonl")
    failed_parts[1].generate.side_effect = RuntimeError("signal failed")
    result = failed.process_candle(_market())
    assert result.outcome is CandleOutcome.FAILED and result.error_stage is PipelineStage.SIGNAL
    failed_parts[2].decide.assert_not_called(); failed_parts[3].assess.assert_not_called(); failed_parts[4].execute.assert_not_called()


@pytest.mark.parametrize("status", [ExecutionStatus.REJECTED, ExecutionStatus.PARTIALLY_FILLED, ExecutionStatus.UNKNOWN])
def test_broker_results_are_forwarded_and_position_consistent(tmp_path: Path, status: ExecutionStatus) -> None:
    runner, parts = _runner(tmp_path, execution=status)
    result = runner.process_candle(_market())
    assert result.execution_result.execution_status is status
    parts[6].forward_execution.assert_called_once()
    expected = PositionLifecycle.PARTIALLY_FILLED if status is ExecutionStatus.PARTIALLY_FILLED else PositionLifecycle.REJECTED
    assert result.position_snapshot.current_state is expected


def test_deterministic_replay_and_full_persisted_chain_integrity(tmp_path: Path) -> None:
    first, _ = _runner(tmp_path, log_name="first.jsonl")
    second, _ = _runner(tmp_path, log_name="second.jsonl")
    left, right = first.process_candle(_market()), second.process_candle(_market())
    assert [event.canonical_json() for event in left.events] == [event.canonical_json() for event in right.events]
    persisted = first.event_log.read_all()
    RuntimeEventLog.verify(persisted)
    assert len(persisted) == 7
    assert all(current.previous_event_id == previous.event_id for previous, current in zip(persisted, persisted[1:]))