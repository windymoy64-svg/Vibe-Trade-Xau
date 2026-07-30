"""Immutable contracts for read-only runtime integration harness results."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pydantic import Field, field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract, validate_identifier_segment
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.serialization import canonical_json
from src.aios.runtime_adapter.contracts import RuntimeEvent


class HarnessSession(FrozenContract):
    """Deterministic descriptor for one externally supplied ingestion batch."""

    session_id: str
    adapter_id: str
    opened_at: datetime
    expected_event_count: int = Field(ge=0)
    execution_authority: str = "existing-runtime"
    evidence_only: bool = True

    @field_validator("session_id", "adapter_id", mode="before")
    @classmethod
    def _identifier(cls, value: str, info: Any) -> str:
        return validate_identifier_segment(value, field_name=info.field_name)

    @field_validator("opened_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("opened_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("execution_authority")
    @classmethod
    def _authority(cls, value: str) -> str:
        if value != "existing-runtime":
            raise ValueError("harness sessions must retain existing-runtime authority")
        return value

    @field_validator("evidence_only")
    @classmethod
    def _evidence_only(cls, value: bool) -> bool:
        if not value:
            raise ValueError("harness sessions must remain evidence-only")
        return value

    def canonical_json(self) -> str:
        return canonical_json(self)


class IngestionOutcome(FrozenContract):
    """Immutable result for one externally supplied input item."""

    input_index: int = Field(ge=0)
    accepted: bool
    event_id: str | None = None
    sequence_id: int | None = Field(default=None, ge=0)
    evidence_id: str | None = None
    evidence_digest: str | None = None
    error_kind: str | None = None
    error_message: str | None = None

    @field_validator("event_id", "evidence_id", "error_kind", mode="before")
    @classmethod
    def _optional_identifier(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return validate_identifier_segment(value, field_name=info.field_name)

    @field_validator("evidence_digest")
    @classmethod
    def _digest(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("evidence_digest must be a SHA-256 hex digest")
        return normalized

    @model_validator(mode="after")
    def _consistent(self) -> "IngestionOutcome":
        evidence_fields = (self.evidence_id, self.evidence_digest)
        error_fields = (self.error_kind, self.error_message)
        if self.accepted:
            if self.event_id is None or self.sequence_id is None or any(item is None for item in evidence_fields):
                raise ValueError("accepted outcomes require event and evidence identity")
            if any(item is not None for item in error_fields):
                raise ValueError("accepted outcomes cannot contain errors")
        else:
            if any(item is not None for item in evidence_fields):
                raise ValueError("rejected outcomes cannot contain evidence identity")
            if any(item is None for item in error_fields):
                raise ValueError("rejected outcomes require error details")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)


class HarnessReport(FrozenContract):
    """Immutable aggregate of one ingestion session."""

    session: HarnessSession
    outcomes: tuple[IngestionOutcome, ...] = ()
    accepted_events: tuple[RuntimeEvent, ...] = ()
    accepted_evidence: tuple[EvidenceRecord, ...] = ()
    accepted_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    validation_failure_count: int = Field(ge=0)
    conversion_count: int = Field(ge=0)

    @field_validator("outcomes")
    @classmethod
    def _ordered_outcomes(cls, value: tuple[IngestionOutcome, ...]) -> tuple[IngestionOutcome, ...]:
        if tuple(item.input_index for item in value) != tuple(range(len(value))):
            raise ValueError("harness outcomes must be contiguous and input-ordered")
        return value

    @field_validator("accepted_evidence")
    @classmethod
    def _evidence_matches(cls, value: tuple[EvidenceRecord, ...]) -> tuple[EvidenceRecord, ...]:
        if any(not item.verify().verified for item in value):
            raise ValueError("harness report cannot contain unverified evidence")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "HarnessReport":
        if len(self.outcomes) != self.session.expected_event_count:
            raise ValueError("harness outcome count must match expected event count")
        accepted = sum(item.accepted for item in self.outcomes)
        rejected = len(self.outcomes) - accepted
        validation_failures = sum(item.error_kind == "validation" for item in self.outcomes)
        if self.accepted_count != accepted or self.rejected_count != rejected:
            raise ValueError("harness accepted/rejected counts are inconsistent")
        if self.validation_failure_count != validation_failures:
            raise ValueError("harness validation failure count is inconsistent")
        if (
            self.conversion_count != len(self.accepted_events)
            or self.conversion_count != len(self.accepted_evidence)
            or self.conversion_count != accepted
        ):
            raise ValueError("harness conversion count is inconsistent")
        event_ids = tuple(item.event_id for item in self.outcomes if item.accepted)
        if event_ids != tuple(item.event_id for item in self.accepted_events):
            raise ValueError("harness outcomes and accepted events are misaligned")
        evidence_ids = tuple(item.evidence_id for item in self.outcomes if item.accepted)
        if evidence_ids != tuple(item.evidence_id for item in self.accepted_evidence):
            raise ValueError("harness outcomes and accepted evidence are misaligned")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)


    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class ReplayHarnessResult(FrozenContract):
    """Immutable comparison of original and replayed evidence projections."""

    session_id: str
    adapter_id: str
    compared_count: int = Field(ge=0)
    matched_count: int = Field(ge=0)
    identical: bool
    differences: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> "ReplayHarnessResult":
        if self.matched_count > self.compared_count:
            raise ValueError("replay matched count cannot exceed compared count")
        if self.identical != (not self.differences and self.matched_count == self.compared_count):
            raise ValueError("replay identity status is inconsistent")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)
