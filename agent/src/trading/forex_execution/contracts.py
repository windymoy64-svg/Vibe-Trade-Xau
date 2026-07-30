"""Immutable contracts for the runtime MT5 order-execution boundary."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExecutionStatus(str, Enum):
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class MT5TradingProfile(BaseModel):
    """Caller-supplied profile and broker metadata; no credentials are accepted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_name: str
    trade_mode: str
    trading_enabled: bool = True
    market_available: bool = True
    session_open: bool = True
    stop_level_distance: float = Field(ge=0.0)
    freeze_level_distance: float = Field(ge=0.0)
    filling_mode: str
    execution_mode: str
    expiration_policy: str

    @field_validator("profile_name", "trade_mode", "filling_mode", "execution_mode", "expiration_policy")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("MT5 profile metadata must not be empty")
        return value

    @field_validator("stop_level_distance", "freeze_level_distance")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("MT5 profile distances must be finite")
        return value


class BrokerCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    retcode: int | str | None = None
    comment: str = ""


class BrokerExecutionResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    retcode: int | str | None
    comment: str = ""
    order_ticket: int | None = Field(default=None, gt=0)
    deal_ticket: int | None = Field(default=None, gt=0)
    position_ticket: int | None = Field(default=None, gt=0)
    filled_volume: float = Field(default=0.0, ge=0.0)
    filled_price: float | None = None
    result_class: ExecutionStatus | None = None

    @field_validator("filled_volume", "filled_price")
    @classmethod
    def _finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("broker response numeric fields must be finite")
        return value


class ExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_id: UUID
    order_plan_id: UUID
    intent_id: UUID
    symbol: str
    action: str
    execution_status: ExecutionStatus
    mt5_order_ticket: int | None
    mt5_deal_ticket: int | None
    mt5_position_ticket: int | None
    broker_retcode: int | str | None
    broker_comment: str
    filled_volume: float = Field(ge=0.0)
    filled_price: float | None
    execution_time: datetime
    replay_hash: str

    @field_validator("execution_id")
    @classmethod
    def _uuid7(cls, value: UUID) -> UUID:
        if value.version != 7:
            raise ValueError("execution_id must be UUIDv7")
        return value

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("execution symbol must not be empty")
        return value

    @field_validator("execution_time")
    @classmethod
    def _time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("execution_time must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("filled_volume", "filled_price")
    @classmethod
    def _finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("execution numeric fields must be finite")
        return value

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
