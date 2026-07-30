"""Immutable contracts for runtime forex risk approval."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ApprovalStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RiskPositionDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class RiskPositionSnapshot(BaseModel):
    """Minimal immutable owned-position evidence required to approve an exit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    position_ticket: int = Field(gt=0)
    direction: RiskPositionDirection
    volume_lots: float = Field(gt=0.0)
    owned: bool

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("risk position symbol must not be empty")
        return value

    @field_validator("volume_lots")
    @classmethod
    def _finite_volume(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("risk position volume must be finite")
        return value


class AccountSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    broker_timestamp: datetime
    equity: float = Field(gt=0.0)
    free_margin: float = Field(ge=0.0)
    margin_level: float = Field(ge=0.0)
    leverage: float = Field(gt=0.0)
    daily_loss: float = Field(ge=0.0)
    drawdown_percent: float = Field(ge=0.0)
    trades_today: int = Field(ge=0)
    consecutive_losses: int = Field(ge=0)
    symbol_exposure: float = Field(ge=0.0)
    correlated_exposure: float = Field(ge=0.0)

    @field_validator("broker_timestamp")
    @classmethod
    def _timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("account timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator(
        "equity", "free_margin", "margin_level", "leverage", "daily_loss",
        "drawdown_percent", "symbol_exposure", "correlated_exposure",
    )
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("account values must be finite")
        return value


class SymbolSpecification(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    trading_enabled: bool = True
    market_available: bool = True
    session_open: bool = True
    tick_size: float = Field(gt=0.0)
    tick_value_per_lot: float = Field(gt=0.0)
    contract_size: float = Field(gt=0.0)
    lot_step: float = Field(gt=0.0)
    min_lot: float = Field(gt=0.0)
    max_lot: float = Field(gt=0.0)
    stop_level_distance: float = Field(ge=0.0)
    freeze_level_distance: float = Field(ge=0.0)

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("symbol specification symbol must not be empty")
        return value

    @field_validator(
        "tick_size", "tick_value_per_lot", "contract_size", "lot_step", "min_lot",
        "max_lot", "stop_level_distance", "freeze_level_distance",
    )
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("symbol specification values must be finite")
        return value

    @model_validator(mode="after")
    def _limits(self) -> "SymbolSpecification":
        if self.max_lot < self.min_lot:
            raise ValueError("max_lot must be >= min_lot")
        return self


class RiskConfiguration(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    risk_percent: float = Field(gt=0.0, le=100.0)
    stop_loss_distance: float | None = None
    reward_ratio: float = Field(default=2.0, gt=0.0)
    max_spread: float = Field(gt=0.0)
    min_free_margin: float = Field(ge=0.0)
    min_margin_level: float = Field(ge=0.0)
    max_daily_loss: float = Field(ge=0.0)
    max_drawdown_percent: float = Field(ge=0.0)
    max_trades_per_day: int = Field(ge=0)
    max_consecutive_losses: int = Field(ge=0)
    max_symbol_exposure: float = Field(ge=0.0)
    max_correlated_exposure: float = Field(ge=0.0)
    max_slippage: float = Field(ge=0.0)
    expiration_seconds: int = Field(default=60, gt=0)

    @field_validator(
        "risk_percent", "reward_ratio", "max_spread", "min_free_margin", "min_margin_level",
        "max_daily_loss", "max_drawdown_percent", "max_symbol_exposure",
        "max_correlated_exposure", "max_slippage",
    )
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("risk configuration values must be finite")
        return value

    @field_validator("stop_loss_distance")
    @classmethod
    def _stop_distance(cls, value: float | None) -> float | None:
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError("stop_loss_distance must be positive and finite")
        return value


class ApprovedOrderPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    order_plan_id: UUID
    intent_id: UUID
    symbol: str
    action: str
    volume_lots: float = Field(ge=0.0)
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    risk_percent: float = Field(ge=0.0, le=100.0)
    risk_amount: float = Field(ge=0.0)
    reward_ratio: float = Field(ge=0.0)
    max_slippage: float = Field(ge=0.0)
    expiration: datetime
    approval_status: ApprovalStatus
    rejection_reason: str | None
    replay_hash: str

    @field_validator("order_plan_id", "intent_id")
    @classmethod
    def _uuid7(cls, value: UUID) -> UUID:
        if value.version != 7:
            raise ValueError("order plan identifiers must be UUIDv7")
        return value

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("order plan symbol must not be empty")
        return value

    @field_validator("expiration")
    @classmethod
    def _expiration(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expiration must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator(
        "volume_lots", "risk_percent", "risk_amount", "reward_ratio", "max_slippage",
        "entry_price", "stop_loss", "take_profit",
    )
    @classmethod
    def _finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("order plan numeric values must be finite")
        return value

    @field_validator("replay_hash")
    @classmethod
    def _hash(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("replay_hash must be lowercase SHA-256 hex")
        return value

    @model_validator(mode="after")
    def _approval_consistency(self) -> "ApprovedOrderPlan":
        if self.approval_status is ApprovalStatus.APPROVED:
            if self.rejection_reason is not None:
                raise ValueError("approved plans cannot have rejection_reason")
            if self.volume_lots <= 0 or self.entry_price is None:
                raise ValueError("approved plans require volume and entry price")
            if self.action == "CLOSE_POSITION":
                # Exit plans may omit protective prices; legacy callers that include
                # them remain structurally compatible, while the Risk Manager never
                # calculates or relies on them for CLOSE_POSITION.
                pass
            elif self.stop_loss is None or self.take_profit is None:
                raise ValueError("approved entry plans require stop loss and take profit")
        elif not self.rejection_reason:
            raise ValueError("rejected plans require rejection_reason")
        return self

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
