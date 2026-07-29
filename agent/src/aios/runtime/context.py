"""Immutable Research-only runtime observation context."""
from __future__ import annotations
from datetime import datetime, timezone
from pydantic import field_validator, model_validator
from src.aios.contracts.environment import ExecutionEnvironment
from src.aios.contracts.identifiers import CorrelationId, FrozenContract


class RuntimeContext(FrozenContract):
    run_id: CorrelationId
    environment: ExecutionEnvironment = ExecutionEnvironment.RESEARCH
    observed_at: datetime
    manifest_digest: str
    labels: tuple[tuple[str, str], ...] = ()

    @field_validator("observed_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _research_only(self) -> "RuntimeContext":
        if self.environment != ExecutionEnvironment.RESEARCH:
            raise ValueError("Phase 5 runtime context is research-only")
        if tuple(sorted(self.labels)) != self.labels:
            raise ValueError("labels must be sorted")
        return self