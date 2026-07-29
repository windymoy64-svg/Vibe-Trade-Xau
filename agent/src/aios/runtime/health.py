"""Immutable dependency-health evidence."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pydantic import field_validator
from src.aios.contracts.identifiers import FrozenContract, ResourceId


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DependencyHealth(FrozenContract):
    dependency: ResourceId
    state: HealthState = HealthState.UNKNOWN
    detail: str = ""
    evidence_refs: tuple[str, ...] = ()


class HealthSnapshot(FrozenContract):
    snapshot_id: str
    observed_at: datetime
    dependencies: tuple[DependencyHealth, ...] = ()
    authoritative: bool = False

    @field_validator("observed_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(timezone.utc)