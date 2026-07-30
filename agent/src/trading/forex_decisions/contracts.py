"""Immutable input/output contracts for runtime forex decisions."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

DECISION_STRATEGY_NAME = "forex-ema-macd-rsi-baseline"
DECISION_STRATEGY_VERSION = "1.0.0"


class PositionState(str, Enum):
    FLAT = "FLAT"
    LONG = "LONG"
    SHORT = "SHORT"
    PENDING_ENTRY = "PENDING_ENTRY"
    PENDING_EXIT = "PENDING_EXIT"


class ACTION(str, Enum):
    HOLD = "HOLD"
    OPEN_LONG = "OPEN_LONG"
    OPEN_SHORT = "OPEN_SHORT"
    CLOSE_POSITION = "CLOSE_POSITION"
    REVERSE_TO_LONG = "REVERSE_TO_LONG"
    REVERSE_TO_SHORT = "REVERSE_TO_SHORT"


ALLOWED_ACTIONS = frozenset(action.value for action in ACTION)


class PositionStateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    state: PositionState

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("position symbol must not be empty")
        return value


class PendingOrdersState(BaseModel):
    """Read-only pending-order summary consumed by the decision boundary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    has_pending_orders: bool = False
    state: PositionState | None = None

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("pending-order symbol must not be empty")
        return value


class QuoteSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    timeframe: str
    broker_timestamp: datetime
    bid: float
    ask: float
    spread: float = Field(ge=0.0)

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("quote symbol must not be empty")
        return value

    @field_validator("broker_timestamp")
    @classmethod
    def _timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("quote timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("bid", "ask", "spread")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("quote values must be finite")
        return value

    @field_validator("bid", "ask")
    @classmethod
    def _positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("quote prices must be positive")
        return value


class StrategyRuntimeState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    strategy_name: str = DECISION_STRATEGY_NAME
    strategy_version: str = DECISION_STRATEGY_VERSION

    @field_validator("strategy_name", "strategy_version")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("strategy runtime identifiers must not be empty")
        return value


class DecisionSnapshot(BaseModel):
    """Immutable deterministic decision for one signal candle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    decision_id: UUID
    intent_id: UUID
    symbol: str
    timeframe: str
    broker_timestamp: datetime
    signal_id: UUID
    signal_type: str
    action: ACTION
    current_position_state: PositionState
    target_position_state: PositionState
    reason_codes: tuple[str, ...]
    replay_hash: str

    @field_validator("decision_id", "intent_id")
    @classmethod
    def _uuid7(cls, value: UUID) -> UUID:
        if value.version != 7:
            raise ValueError("decision identifiers must be UUIDv7")
        return value

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("decision symbol must not be empty")
        return value

    @field_validator("broker_timestamp")
    @classmethod
    def _timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("reason_codes")
    @classmethod
    def _reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("decision reason_codes must not be empty")
        canonical = tuple(sorted(set(value)))
        if any(not reason or reason.upper() != reason or reason.strip() != reason for reason in canonical):
            raise ValueError("decision reason codes must be canonical uppercase values")
        return canonical

    @field_validator("replay_hash")
    @classmethod
    def _hash(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("replay_hash must be lowercase SHA-256 hex")
        return value

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
