"""Generic deterministic governance decision envelopes."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import field_validator

from src.aios.contracts.identifiers import FrozenContract


class DecisionOutcome(str, Enum):
    PERMIT = "permit"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"
    ERROR = "error"


class GovernanceDecision(FrozenContract):
    """Auditable result; evaluation behavior belongs to later phases."""

    decision_id: str
    subject_digest: str
    outcome: DecisionOutcome
    decided_at: datetime
    reason_code: str
    rationale: str
    policy_refs: tuple[str, ...] = ()

    @field_validator("decided_at")
    @classmethod
    def _normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decided_at must be timezone-aware")
        return value.astimezone(timezone.utc)
