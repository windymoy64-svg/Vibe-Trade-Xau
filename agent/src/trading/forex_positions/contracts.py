"""Immutable MT5 evidence and position-state contracts."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PositionLifecycle(str, Enum):
    FLAT = "FLAT"
    PENDING_ENTRY = "PENDING_ENTRY"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    PENDING_EXIT = "PENDING_EXIT"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class AccountPolicy(str, Enum):
    HEDGING = "HEDGING"
    NETTING = "NETTING"


class _OwnedRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    magic_number: int
    comment: str
    strategy_name: str
    strategy_version: str
    intent_id: UUID | None = None

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("MT5 record symbol must not be empty")
        return value


class MT5PositionEntry(_OwnedRecord):
    ticket: int = Field(gt=0)
    order_ticket: int | None = Field(default=None, gt=0)
    deal_ticket: int | None = Field(default=None, gt=0)
    direction: Direction
    volume_lots: float = Field(gt=0.0)
    entry_price: float = Field(gt=0.0)
    stop_loss: float | None = None
    take_profit: float | None = None
    open_time: datetime
    update_time: datetime

    @field_validator("volume_lots", "entry_price", "stop_loss", "take_profit")
    @classmethod
    def _finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("position values must be finite")
        return value

    @field_validator("open_time", "update_time")
    @classmethod
    def _time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("position times must be timezone-aware")
        return value.astimezone(timezone.utc)


class PendingOrderEntry(_OwnedRecord):
    ticket: int = Field(gt=0)
    direction: Direction
    requested_volume: float = Field(gt=0.0)
    remaining_volume: float = Field(ge=0.0)
    is_exit: bool = False
    rejected: bool = False
    setup_time: datetime

    @field_validator("requested_volume", "remaining_volume")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("pending-order volumes must be finite")
        return value

    @field_validator("setup_time")
    @classmethod
    def _time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("pending order time must be timezone-aware")
        return value.astimezone(timezone.utc)


class DealEntry(_OwnedRecord):
    ticket: int = Field(gt=0)
    order_ticket: int = Field(gt=0)
    position_ticket: int | None = Field(default=None, gt=0)
    direction: Direction
    volume_lots: float = Field(ge=0.0)
    price: float = Field(ge=0.0)
    is_exit: bool = False
    rejected: bool = False
    deal_time: datetime

    @field_validator("volume_lots", "price")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("deal values must be finite")
        return value

    @field_validator("deal_time")
    @classmethod
    def _time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("deal time must be timezone-aware")
        return value.astimezone(timezone.utc)


class MT5PositionSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    captured_at: datetime
    positions: tuple[MT5PositionEntry, ...] = ()

    @field_validator("captured_at")
    @classmethod
    def _time(cls, value: datetime) -> datetime:
        return _aware(value)


class PendingOrdersSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    captured_at: datetime
    orders: tuple[PendingOrderEntry, ...] = ()

    @field_validator("captured_at")
    @classmethod
    def _time(cls, value: datetime) -> datetime:
        return _aware(value)


class DealHistorySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    captured_at: datetime
    deals: tuple[DealEntry, ...] = ()

    @field_validator("captured_at")
    @classmethod
    def _time(cls, value: datetime) -> datetime:
        return _aware(value)


class PositionStateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    position_state_id: UUID
    strategy_position_id: UUID
    symbol: str
    strategy_name: str
    strategy_version: str
    magic_number: int
    comment: str
    mt5_position_ticket: int | None
    mt5_order_ticket: int | None
    mt5_deal_ticket: int | None
    current_state: PositionLifecycle
    direction: Direction
    volume_lots: float = Field(ge=0.0)
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    open_time: datetime | None
    last_update_time: datetime
    replay_hash: str

    @field_validator("position_state_id", "strategy_position_id")
    @classmethod
    def _uuid7(cls, value: UUID) -> UUID:
        if value.version != 7:
            raise ValueError("position identifiers must be UUIDv7")
        return value

    @field_validator("last_update_time", "open_time")
    @classmethod
    def _time(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _aware(value)

    @field_validator("volume_lots", "entry_price", "stop_loss", "take_profit")
    @classmethod
    def _finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("position snapshot values must be finite")
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


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("snapshot time must be timezone-aware")
    return value.astimezone(timezone.utc)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
