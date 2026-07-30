"""Immutable value models for Trading Memory Schema v1.0."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FrozenMemoryModel(BaseModel):
    """Strict, immutable base for persisted trading-memory facts."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=True)


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeOutcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAK_EVEN = "BREAK EVEN"


class ExitReason(str, Enum):
    TP = "TP"
    SL = "SL"
    MANUAL_EXIT = "Manual Exit"
    TRAILING_EXIT = "Trailing Exit"


class Identity(FrozenMemoryModel):
    memory_id: UUID = Field(default_factory=uuid4)
    trade_id: str = Field(min_length=1)
    replay_id: str | None = None
    experiment_id: str | None = None
    walkforward_id: str | None = None
    strategy_version: str = Field(min_length=1)
    runtime_config_version: str = Field(min_length=1)
    git_commit: str | None = None
    timestamp: datetime
    environment: str = Field(min_length=1)

    @field_validator("timestamp")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class MarketContext(FrozenMemoryModel):
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    session: str | None = None
    market_regime: str | None = None
    trend: str | None = None
    volatility_state: str | None = None
    liquidity_state: str | None = None
    spread: float | None = Field(default=None, ge=0)
    atr: float | None = Field(default=None, ge=0)
    volume_ratio: float | None = Field(default=None, ge=0)
    market_open: bool | None = None
    holiday_flag: bool | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)


class TechnicalSnapshot(FrozenMemoryModel):
    ema: float | dict[str, float] | None = None
    rsi: float | None = None
    macd: float | dict[str, float] | None = None
    atr: float | None = Field(default=None, ge=0)
    volume_ratio: float | None = Field(default=None, ge=0)
    trend_score: float | None = None
    momentum_score: float | None = None
    signal_score: float | None = None
    features: dict[str, Any] = Field(default_factory=dict)


class FundamentalSnapshot(FrozenMemoryModel):
    economic_news: list[dict[str, Any]] | None = None
    news_impact: str | float | None = None
    usd_index: float | None = None
    bond_yield: float | None = None
    gold_etf_flow: float | None = None
    vix: float | None = None
    sentiment: str | float | None = None
    correlation: dict[str, float] | None = None
    future_news_engine: dict[str, Any] | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)


class DecisionSnapshot(FrozenMemoryModel):
    direction: Direction
    confidence: float | None = Field(default=None, ge=0, le=1)
    entry_reasons: tuple[str, ...] = ()
    signal_components: dict[str, Any] = Field(default_factory=dict)
    expected_probability: float | None = Field(default=None, ge=0, le=1)
    expected_rr: float | None = Field(default=None, ge=0)
    expected_holding_time: float | None = Field(default=None, ge=0, description="Expected duration in seconds")
    extensions: dict[str, Any] = Field(default_factory=dict)


class RiskSnapshot(FrozenMemoryModel):
    risk_percent: float = Field(ge=0)
    lot_size: float = Field(gt=0)
    entry: float = Field(gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    rr: float | None = Field(default=None, ge=0)
    atr_stop: float | None = Field(default=None, ge=0)
    position_size: float = Field(gt=0)
    extensions: dict[str, Any] = Field(default_factory=dict)


class ExecutionSnapshot(FrozenMemoryModel):
    executed_entry: float = Field(gt=0)
    executed_exit: float = Field(gt=0)
    slippage: float | None = None
    spread: float | None = Field(default=None, ge=0)
    commission: float | None = None
    swap: float | None = None
    execution_latency: float | None = Field(default=None, ge=0, description="Latency in milliseconds")
    duration: float = Field(ge=0, description="Trade duration in seconds")
    extensions: dict[str, Any] = Field(default_factory=dict)


class ResultSnapshot(FrozenMemoryModel):
    outcome: TradeOutcome
    exit_reason: ExitReason
    profit_usd: float
    profit_percent: float
    profit_r: float
    pips: float
    extensions: dict[str, Any] = Field(default_factory=dict)


class PostMortem(FrozenMemoryModel):
    observations: tuple[str, ...] = ()
    extensions: dict[str, Any] = Field(default_factory=dict)


class LessonPlaceholder(FrozenMemoryModel):
    lesson: str | None = None
    lesson_type: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    created_by: str | None = None
    status: str | None = None


class ValidationSnapshot(FrozenMemoryModel):
    replay_version: str | None = None
    analytics_version: str | None = None
    walkforward_version: str | None = None
    experiment_version: str | None = None
    production_version: str | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)
