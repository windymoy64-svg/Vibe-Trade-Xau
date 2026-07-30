"""Acceptance tests for the pure Runtime Forex Decision Engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.trading.forex_decisions import (
    ACTION,
    DuplicateDecisionError,
    InvalidDecisionInputError,
    PendingOrdersState,
    PositionState,
    PositionStateSnapshot,
    QuoteSnapshot,
    RuntimeDecisionEngine,
    StaleQuoteError,
    StaleSignalError,
    StrategyRuntimeState,
)
from src.trading.forex_features import FEATURE_VERSION, FeatureParameters, FeatureSnapshot, WarmupStatus
from src.trading.forex_signals import RuntimeSignalEngine, SignalSnapshot

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)


def _feature(kind: str, index: int = 0) -> FeatureSnapshot:
    configurations = {
        "LONG": (110.0, 105.0, 100.0, 1.0, 65.0),
        "SHORT": (90.0, 95.0, 100.0, -1.0, 35.0),
        "HOLD": (101.0, 100.0, 99.0, -0.5, 50.0),
    }
    ema20, ema50, ema200, histogram, rsi = configurations[kind]
    return FeatureSnapshot(
        symbol="XAUUSD",
        timeframe="1h",
        broker_timestamp=NOW - timedelta(minutes=30) + timedelta(minutes=index),
        feature_version=FEATURE_VERSION,
        parameter_fingerprint=FeatureParameters().fingerprint,
        warmup_status=WarmupStatus.READY,
        warmup_bars_seen=200 + index,
        warmup_bars_required=200,
        feature_values={
            "ema_20": ema20,
            "ema_50": ema50,
            "ema_200": ema200,
            "macd_histogram": histogram,
            "rsi_14": rsi,
        },
    )


def _signal(kind: str, index: int = 0) -> SignalSnapshot:
    signal_engine = RuntimeSignalEngine(clock=lambda: NOW, stale_after=timedelta(days=1))
    if kind != "EXIT":
        return signal_engine.generate(_feature(kind, index))
    signal_engine.generate(_feature("LONG", index))
    invalidated = _feature("HOLD", index + 1).model_copy(
        update={
            "feature_values": {
                "ema_20": 99.0,
                "ema_50": 101.0,
                "ema_200": 100.0,
                "macd_histogram": -0.1,
                "rsi_14": 50.0,
            }
        }
    )
    return signal_engine.generate(invalidated)


def _position(state: PositionState) -> PositionStateSnapshot:
    return PositionStateSnapshot(symbol="XAUUSD", state=state)


def _pending(*, has_orders: bool = False, state: PositionState | None = None) -> PendingOrdersState:
    return PendingOrdersState(symbol="XAUUSD", has_pending_orders=has_orders, state=state)


def _quote(timestamp: datetime | None = None) -> QuoteSnapshot:
    return QuoteSnapshot(
        symbol="XAUUSD",
        timeframe="1h",
        broker_timestamp=timestamp or NOW - timedelta(seconds=5),
        bid=2400.0,
        ask=2400.2,
        spread=0.2,
    )


def _strategy(version: str = "1.0.0") -> StrategyRuntimeState:
    return StrategyRuntimeState(strategy_version=version)


def _engine(stale_after: timedelta = timedelta(hours=1)) -> RuntimeDecisionEngine:
    return RuntimeDecisionEngine(clock=lambda: NOW, stale_after=stale_after)


def _decide(signal: SignalSnapshot, state: PositionState, *, engine=None, quote=None):  # type: ignore[no-untyped-def]
    return (engine or _engine()).decide(
        signal,
        _position(state),
        _pending(),
        quote or _quote(),
        _strategy(),
    )


def test_hold_action() -> None:
    decision = _decide(_signal("HOLD"), PositionState.FLAT)
    assert decision.action is ACTION.HOLD
    assert decision.target_position_state is PositionState.FLAT
    assert "NO_ACTION" in decision.reason_codes


def test_open_long_action() -> None:
    decision = _decide(_signal("LONG"), PositionState.FLAT)
    assert decision.action is ACTION.OPEN_LONG
    assert decision.target_position_state is PositionState.LONG


def test_open_short_action() -> None:
    decision = _decide(_signal("SHORT"), PositionState.FLAT)
    assert decision.action is ACTION.OPEN_SHORT
    assert decision.target_position_state is PositionState.SHORT


@pytest.mark.parametrize("state", [PositionState.LONG, PositionState.SHORT])
def test_close_position_action(state: PositionState) -> None:
    decision = _decide(_signal("EXIT"), state)
    assert decision.action is ACTION.CLOSE_POSITION
    assert decision.target_position_state is PositionState.FLAT


def test_reverse_to_long_action() -> None:
    decision = _decide(_signal("LONG"), PositionState.SHORT)
    assert decision.action is ACTION.REVERSE_TO_LONG
    assert decision.target_position_state is PositionState.LONG
    assert "REVERSAL" in decision.reason_codes


def test_reverse_to_short_action() -> None:
    decision = _decide(_signal("SHORT"), PositionState.LONG)
    assert decision.action is ACTION.REVERSE_TO_SHORT
    assert decision.target_position_state is PositionState.SHORT
    assert "REVERSAL" in decision.reason_codes


def test_pending_states_fail_safe_to_hold() -> None:
    engine = _engine()
    decision = engine.decide(
        _signal("LONG"),
        _position(PositionState.PENDING_ENTRY),
        _pending(has_orders=True, state=PositionState.PENDING_ENTRY),
        _quote(),
        _strategy(),
    )
    assert decision.action is ACTION.HOLD
    assert decision.target_position_state is PositionState.PENDING_ENTRY
    assert "PENDING_STATE" in decision.reason_codes


def test_duplicate_candle_and_signal_id_rejected() -> None:
    engine = _engine()
    signal = _signal("LONG")
    _decide(signal, PositionState.FLAT, engine=engine)
    with pytest.raises(DuplicateDecisionError):
        _decide(signal, PositionState.FLAT, engine=engine)


def test_stale_signal_rejected() -> None:
    with pytest.raises(StaleSignalError):
        _decide(_signal("LONG"), PositionState.FLAT, engine=_engine(timedelta(minutes=1)))


def test_stale_quote_rejected() -> None:
    with pytest.raises(StaleQuoteError):
        _decide(
            _signal("LONG"),
            PositionState.FLAT,
            quote=_quote(NOW - timedelta(hours=2)),
        )


def test_deterministic_replay() -> None:
    signal = _signal("LONG")
    inputs = ((signal, _position(PositionState.FLAT), _pending(), _quote(), _strategy()),)
    first = _engine().replay(inputs)
    second = _engine().replay(inputs)
    assert first[0].canonical_json() == second[0].canonical_json()
    assert first[0].decision_id == second[0].decision_id
    assert first[0].intent_id == second[0].intent_id


def test_decision_snapshot_is_immutable_and_uuidv7() -> None:
    decision = _decide(_signal("LONG"), PositionState.FLAT)
    assert isinstance(decision.decision_id, UUID) and decision.decision_id.version == 7
    assert isinstance(decision.intent_id, UUID) and decision.intent_id.version == 7
    with pytest.raises(ValidationError):
        decision.action = ACTION.HOLD  # type: ignore[misc]
    with pytest.raises(TypeError):
        decision.reason_codes[0] = "CHANGED"  # type: ignore[index]


def test_replay_hash_stability_and_signal_binding() -> None:
    signal = _signal("SHORT")
    first = _decide(signal, PositionState.FLAT)
    second = _decide(signal, PositionState.FLAT)
    assert first.replay_hash == second.replay_hash
    assert len(first.replay_hash) == 64
    assert first.signal_id == signal.signal_id


def test_strategy_version_and_signal_replay_hash_validation() -> None:
    signal = _signal("LONG")
    with pytest.raises(InvalidDecisionInputError, match="strategy version mismatch"):
        _engine().decide(signal, _position(PositionState.FLAT), _pending(), _quote(), _strategy("2.0.0"))
    tampered = signal.model_copy(update={"replay_hash": "0" * 64})
    with pytest.raises(InvalidDecisionInputError, match="invalid signal replay hash"):
        _decide(tampered, PositionState.FLAT)
