"""Pure deterministic Runtime Forex Decision Engine."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

from src.trading.forex_decisions.contracts import (
    ACTION,
    DECISION_STRATEGY_NAME,
    DECISION_STRATEGY_VERSION,
    DecisionSnapshot,
    PendingOrdersState,
    PositionState,
    PositionStateSnapshot,
    QuoteSnapshot,
    StrategyRuntimeState,
    _canonical_json,
)
from src.trading.forex_signals import STRATEGY_NAME, STRATEGY_VERSION, SignalSnapshot, SignalType
from src.trading.forex_signals.engine import _deterministic_uuid7
from src.trading.runtime_config import RuntimeConfig


class InvalidDecisionInputError(ValueError):
    """An input violates the decision boundary or version contract."""


class DuplicateDecisionError(InvalidDecisionInputError):
    """A candle, signal, or intent was already consumed."""


class StaleSignalError(InvalidDecisionInputError):
    """The input signal is stale or future-dated."""


class StaleQuoteError(InvalidDecisionInputError):
    """The current quote is stale or future-dated."""


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeDecisionEngine:
    """Translate one validated signal/state tuple into one immutable action."""

    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig | None = None,
        clock: Callable[[], datetime] = _default_clock,
        stale_after: timedelta | None = None,
    ) -> None:
        if stale_after is not None and stale_after <= timedelta(0):
            raise ValueError("stale_after must be positive")
        self.runtime_config = runtime_config or RuntimeConfig()
        self._clock = clock
        self._stale_after = stale_after
        self._seen_candles: set[tuple[str, str, datetime]] = set()
        self._seen_signals: set[UUID] = set()
        self._seen_intents: set[UUID] = set()

    def decide(
        self,
        signal: SignalSnapshot,
        position: PositionStateSnapshot,
        pending_orders: PendingOrdersState,
        quote: QuoteSnapshot,
        strategy_state: StrategyRuntimeState,
    ) -> DecisionSnapshot:
        self._validate_inputs(signal, position, pending_orders, quote, strategy_state)
        now = self._now()
        maximum_age = self._stale_after or (_timeframe_duration(signal.timeframe) * 2)
        _reject_age(signal.broker_timestamp, now, maximum_age, StaleSignalError, "signal")
        _reject_age(quote.broker_timestamp, now, maximum_age, StaleQuoteError, "quote")

        candle = (signal.symbol, signal.timeframe, signal.broker_timestamp)
        if candle in self._seen_candles:
            raise DuplicateDecisionError("duplicate candle")
        if signal.signal_id in self._seen_signals:
            raise DuplicateDecisionError("duplicate signal_id")

        action, target, reasons = _resolve_action(signal.signal_type, position.state, pending_orders)
        material = {
            "broker_timestamp": signal.broker_timestamp.isoformat(),
            "current_position_state": position.state.value,
            "intent_action": action.value,
            "signal_id": str(signal.signal_id),
            "signal_type": signal.signal_type.value,
            "strategy_name": strategy_state.strategy_name,
            "strategy_version": strategy_state.strategy_version,
            "symbol": signal.symbol,
            "target_position_state": target.value,
            "timeframe": signal.timeframe,
        }
        intent_id = _deterministic_uuid7(signal.broker_timestamp, _canonical_json(material))
        if intent_id in self._seen_intents:
            raise DuplicateDecisionError("duplicate intent_id")
        decision_material = {
            **material,
            "intent_id": str(intent_id),
            "quote_timestamp": quote.broker_timestamp.isoformat(),
        }
        decision_id = _deterministic_uuid7(signal.broker_timestamp, _canonical_json(decision_material))
        replay_hash = hashlib.sha256(
            _canonical_json(
                {**decision_material, "decision_id": str(decision_id), "reason_codes": tuple(sorted(reasons))}
            ).encode("utf-8")
        ).hexdigest()
        decision = DecisionSnapshot(
            decision_id=decision_id,
            intent_id=intent_id,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            broker_timestamp=signal.broker_timestamp,
            signal_id=signal.signal_id,
            signal_type=signal.signal_type.value,
            action=action,
            current_position_state=position.state,
            target_position_state=target,
            reason_codes=tuple(sorted(reasons)),
            replay_hash=replay_hash,
        )
        self._seen_candles.add(candle)
        self._seen_signals.add(signal.signal_id)
        self._seen_intents.add(intent_id)
        return decision

    def replay(
        self,
        inputs: tuple[
            tuple[SignalSnapshot, PositionStateSnapshot, PendingOrdersState, QuoteSnapshot, StrategyRuntimeState], ...
        ]
        | list[tuple[SignalSnapshot, PositionStateSnapshot, PendingOrdersState, QuoteSnapshot, StrategyRuntimeState]],
    ) -> tuple[DecisionSnapshot, ...]:
        return tuple(self.decide(*item) for item in inputs)

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision engine clock must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _validate_inputs(signal, position, pending_orders, quote, strategy_state) -> None:
        if not isinstance(signal, SignalSnapshot):
            raise InvalidDecisionInputError("decision engine accepts only SignalSnapshot")
        if not isinstance(position, PositionStateSnapshot):
            raise InvalidDecisionInputError("invalid position state")
        if not isinstance(pending_orders, PendingOrdersState):
            raise InvalidDecisionInputError("invalid pending orders state")
        if not isinstance(quote, QuoteSnapshot):
            raise InvalidDecisionInputError("invalid quote snapshot")
        if not isinstance(strategy_state, StrategyRuntimeState):
            raise InvalidDecisionInputError("invalid strategy runtime state")
        if signal.strategy_name != STRATEGY_NAME or signal.strategy_version != STRATEGY_VERSION:
            raise InvalidDecisionInputError("signal version mismatch")
        if not _valid_signal_replay_hash(signal):
            raise InvalidDecisionInputError("invalid signal replay hash")
        if strategy_state.strategy_name != DECISION_STRATEGY_NAME:
            raise InvalidDecisionInputError("strategy name mismatch")
        if strategy_state.strategy_version != DECISION_STRATEGY_VERSION:
            raise InvalidDecisionInputError("strategy version mismatch")
        if position.symbol != signal.symbol or pending_orders.symbol != signal.symbol or quote.symbol != signal.symbol:
            raise InvalidDecisionInputError("input symbol mismatch")
        if quote.timeframe != signal.timeframe:
            raise InvalidDecisionInputError("quote timeframe mismatch")
        if quote.ask < quote.bid:
            raise InvalidDecisionInputError("quote ask is below bid")
        if pending_orders.state is not None and pending_orders.state not in {
            PositionState.PENDING_ENTRY,
            PositionState.PENDING_EXIT,
        }:
            raise InvalidDecisionInputError("unsupported pending order state")


def _resolve_action(
    signal: SignalType, current: PositionState, pending: PendingOrdersState
) -> tuple[ACTION, PositionState, tuple[str, ...]]:
    position_reason = f"POSITION_{current.value}"
    if current in {PositionState.PENDING_ENTRY, PositionState.PENDING_EXIT} or pending.has_pending_orders:
        return ACTION.HOLD, current, ("NO_ACTION", position_reason, "PENDING_STATE", f"SIGNAL_{signal.value}")
    if signal is SignalType.HOLD:
        return ACTION.HOLD, current, ("NO_ACTION", position_reason, "SIGNAL_HOLD")
    if signal is SignalType.LONG:
        if current is PositionState.FLAT:
            return ACTION.OPEN_LONG, PositionState.LONG, ("POSITION_FLAT", "SIGNAL_LONG")
        if current is PositionState.LONG:
            return ACTION.HOLD, current, ("NO_ACTION", "POSITION_LONG", "SIGNAL_LONG")
        if current is PositionState.SHORT:
            return ACTION.REVERSE_TO_LONG, PositionState.LONG, ("POSITION_SHORT", "REVERSAL", "SIGNAL_LONG")
    if signal is SignalType.SHORT:
        if current is PositionState.FLAT:
            return ACTION.OPEN_SHORT, PositionState.SHORT, ("POSITION_FLAT", "SIGNAL_SHORT")
        if current is PositionState.SHORT:
            return ACTION.HOLD, current, ("NO_ACTION", "POSITION_SHORT", "SIGNAL_SHORT")
        if current is PositionState.LONG:
            return ACTION.REVERSE_TO_SHORT, PositionState.SHORT, ("POSITION_LONG", "REVERSAL", "SIGNAL_SHORT")
    if signal is SignalType.EXIT and current in {PositionState.LONG, PositionState.SHORT}:
        return ACTION.CLOSE_POSITION, PositionState.FLAT, (f"POSITION_{current.value}", "SIGNAL_EXIT")
    return ACTION.HOLD, current, ("NO_ACTION", position_reason, f"SIGNAL_{signal.value}")


def _valid_signal_replay_hash(signal: SignalSnapshot) -> bool:
    material = {
        "broker_timestamp": signal.broker_timestamp.isoformat(),
        "confidence": signal.confidence,
        "feature_digest": signal.feature_digest,
        "reason_codes": signal.reason_codes,
        "signal_type": signal.signal_type.value,
        "strategy_name": signal.strategy_name,
        "strategy_version": signal.strategy_version,
        "symbol": signal.symbol,
        "timeframe": signal.timeframe,
    }
    expected = hashlib.sha256(
        _canonical_json({**material, "signal_id": str(signal.signal_id)}).encode("utf-8")
    ).hexdigest()
    return expected == signal.replay_hash


def _reject_age(
    timestamp: datetime, now: datetime, maximum_age: timedelta, error_type: type[ValueError], label: str
) -> None:
    age = now - timestamp
    if age < timedelta(0) or age > maximum_age:
        raise error_type(f"{label} is stale")


_TIMEFRAME_RE = re.compile(r"^(\d+)([mhdwM])$")


def _timeframe_duration(timeframe: str) -> timedelta:
    match = _TIMEFRAME_RE.fullmatch(timeframe)
    if not match:
        raise InvalidDecisionInputError(f"unsupported timeframe: {timeframe!r}")
    amount = int(match.group(1))
    unit = match.group(2)
    if amount <= 0:
        raise InvalidDecisionInputError("timeframe amount must be positive")
    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    if unit == "w":
        return timedelta(weeks=amount)
    return timedelta(days=30 * amount)
