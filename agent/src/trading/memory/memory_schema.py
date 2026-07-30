"""Top-level, versioned Trading Memory Schema."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .memory_models import (
    DecisionSnapshot, ExecutionSnapshot, FrozenMemoryModel, FundamentalSnapshot, Identity,
    LessonPlaceholder, MarketContext, PostMortem, ResultSnapshot, RiskSnapshot,
    TechnicalSnapshot, ValidationSnapshot,
)

SCHEMA_VERSION = "1.0"


class TradingMemory(FrozenMemoryModel):
    """One complete, completed-trade experience."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    identity: Identity
    market_context: MarketContext
    technical_snapshot: TechnicalSnapshot
    fundamental_snapshot: FundamentalSnapshot = Field(default_factory=FundamentalSnapshot)
    decision_snapshot: DecisionSnapshot
    risk_snapshot: RiskSnapshot
    execution_snapshot: ExecutionSnapshot
    result_snapshot: ResultSnapshot
    post_mortem: PostMortem = Field(default_factory=PostMortem)
    lesson: LessonPlaceholder = Field(default_factory=LessonPlaceholder)
    validation_snapshot: ValidationSnapshot = Field(default_factory=ValidationSnapshot)


class TradingMemoryJournal(FrozenMemoryModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    memories: tuple[TradingMemory, ...] = ()
