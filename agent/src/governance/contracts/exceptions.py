"""Scoped and time-bound governance exception contracts."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract, ResourceId
from src.governance.contracts.approvals import Approval


class GovernanceException(FrozenContract):
    """An immutable exception request with explicit scope and expiration."""

    exception_id: str
    subject: ResourceId
    policy_ref: str
    scope: tuple[str, ...]
    justification: str
    valid_from: datetime
    expires_at: datetime
    approvals: tuple[Approval, ...]

    @field_validator("valid_from", "expires_at")
    @classmethod
    def _normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("exception timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_window(self) -> "GovernanceException":
        if self.expires_at <= self.valid_from:
            raise ValueError("expires_at must be later than valid_from")
        if not self.scope:
            raise ValueError("exception scope cannot be empty")
        if not self.approvals:
            raise ValueError("exception requires at least one approval")
        return self
