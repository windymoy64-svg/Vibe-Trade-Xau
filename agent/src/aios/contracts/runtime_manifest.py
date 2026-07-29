"""Immutable resolution manifest contract; no runtime behavior is implemented."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import field_validator

from src.aios.contracts.environment import ExecutionEnvironment, ReleaseChannel
from src.aios.contracts.identifiers import CorrelationId, FrozenContract, ResourceId
from src.aios.contracts.resources import ResourceBudget


class ResolvedReference(FrozenContract):
    """An exact content-addressed dependency selected before execution."""

    resource: ResourceId
    version: str
    digest: str

    @field_validator("digest")
    @classmethod
    def _validate_digest(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
            raise ValueError("digest must be a lowercase SHA-256 hex digest")
        return normalized


class RuntimeManifest(FrozenContract):
    """Pinned evidence describing a run; it does not execute that run."""

    schema_version: int = 1
    run_id: CorrelationId
    environment: ExecutionEnvironment
    release_channel: ReleaseChannel
    resolved_at: datetime
    dependencies: tuple[ResolvedReference, ...]
    resources: ResourceBudget
    policy_decision_ids: tuple[str, ...] = ()
    feature_snapshot_digest: str | None = None
    experiment_id: str | None = None

    @field_validator("resolved_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("resolved_at must be timezone-aware")
        return value.astimezone(timezone.utc)
