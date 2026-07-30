"""Immutable orchestration contracts for the runtime forex pipeline."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class PipelineStage(str, Enum):
    MARKET = "MarketSnapshot"
    FEATURE = "FeatureSnapshot"
    SIGNAL = "SignalSnapshot"
    DECISION = "DecisionSnapshot"
    ORDER_PLAN = "ApprovedOrderPlan"
    EXECUTION = "ExecutionResult"
    POSITION = "PositionStateSnapshot"
    FAILURE = "PipelineFailure"


class CandleOutcome(str, Enum):
    WARMING_UP = "WARMING_UP"
    HOLD = "HOLD"
    RISK_REJECTED = "RISK_REJECTED"
    COMPLETED = "COMPLETED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"


class RuntimeEvent(BaseModel):
    """One immutable, hash-linked event persisted by the pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    previous_event_id: str | None
    stage: PipelineStage
    candle_id: str
    occurred_at: datetime
    payload: dict[str, Any]
    previous_hash: str | None
    event_hash: str

    @field_validator("occurred_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event time must be timezone-aware")
        return value.astimezone(timezone.utc)

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))


class PipelineResult(BaseModel):
    """Fail-closed result for one market-data callback."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    candle_id: str | None
    outcome: CandleOutcome
    events: tuple[RuntimeEvent, ...] = ()
    feature_snapshot: Any = None
    signal_snapshot: Any = None
    decision_snapshot: Any = None
    order_plan: Any = None
    execution_result: Any = None
    position_snapshot: Any = None
    error_stage: PipelineStage | None = None
    error_message: str | None = None


def candle_identity(snapshot: object) -> str:
    """Return the normalized deterministic identity of a closed candle."""
    if isinstance(snapshot, dict):
        symbol = snapshot.get("symbol")
        timeframe = snapshot.get("timeframe")
        timestamp = snapshot.get("broker_timestamp")
    else:
        symbol = getattr(snapshot, "symbol", None)
        timeframe = getattr(snapshot, "timeframe", None)
        timestamp = getattr(snapshot, "broker_timestamp", None)
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("market broker_timestamp must be timezone-aware")
    material = {
        "broker_timestamp": timestamp.astimezone(timezone.utc).isoformat(),
        "symbol": str(symbol or "").strip().upper(),
        "timeframe": str(timeframe or "").strip(),
    }
    if not material["symbol"] or not material["timeframe"]:
        raise ValueError("market symbol and timeframe are required")
    return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)