"""Evidence-only runtime lifecycle observations."""
from __future__ import annotations
from datetime import datetime, timezone
from pydantic import field_validator
from src.aios.contracts.identifiers import FrozenContract
from src.aios.contracts.lifecycle import RuntimeLifecycle, validate_runtime_transition


class LifecycleObservation(FrozenContract):
    current: RuntimeLifecycle
    proposed: RuntimeLifecycle
    observed_at: datetime
    valid: bool
    reason: str

    @field_validator("observed_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(timezone.utc)


def observe_transition(current: RuntimeLifecycle, proposed: RuntimeLifecycle, *, observed_at: datetime) -> LifecycleObservation:
    try:
        validate_runtime_transition(current, proposed)
    except ValueError as exc:
        return LifecycleObservation(current=current, proposed=proposed, observed_at=observed_at, valid=False, reason=str(exc))
    return LifecycleObservation(current=current, proposed=proposed, observed_at=observed_at, valid=True, reason="valid foundation transition")