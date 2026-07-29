"""Immutable governance approval evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.governance.contracts.actors import Actor


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class Approval(FrozenContract):
    """A decision bound to one immutable subject digest."""

    approval_id: str
    subject_digest: str
    approver: Actor
    status: ApprovalStatus
    decided_at: datetime
    reason: str
    expires_at: datetime | None = None

    @field_validator("decided_at", "expires_at")
    @classmethod
    def _normalize_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("approval timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_expiry(self) -> "Approval":
        if self.expires_at is not None and self.expires_at <= self.decided_at:
            raise ValueError("expires_at must be later than decided_at")
        return self
