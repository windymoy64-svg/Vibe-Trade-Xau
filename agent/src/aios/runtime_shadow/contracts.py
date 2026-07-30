"""Immutable evidence-only contracts for controlled shadow evaluation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract, validate_identifier_segment
from src.aios.provenance.serialization import canonical_json


class AssessmentValue(str, Enum):
    """Decision values comparable without assigning execution meaning."""

    APPROVE = "approve"
    DENY = "deny"
    HOLD = "hold"
    UNKNOWN = "unknown"


class ComparisonClassification(str, Enum):
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    INDETERMINATE = "indeterminate"


class ShadowSession(FrozenContract):
    """Immutable descriptor for one controlled comparison session."""

    session_id: str
    runtime_identity: str
    adapter_id: str
    opened_at: datetime
    snapshot_set_digest: str
    execution_authority: str = "existing-runtime"
    evidence_only: bool = True

    @field_validator("session_id", "runtime_identity", "adapter_id", mode="before")
    @classmethod
    def _identifier(cls, value: str, info: Any) -> str:
        return validate_identifier_segment(value, field_name=info.field_name)

    @field_validator("opened_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("opened_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("snapshot_set_digest")
    @classmethod
    def _digest(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("snapshot_set_digest must be a SHA-256 hex digest")
        return normalized

    @field_validator("execution_authority")
    @classmethod
    def _authority(cls, value: str) -> str:
        if value != "existing-runtime":
            raise ValueError("shadow sessions must retain existing-runtime authority")
        return value

    @field_validator("evidence_only")
    @classmethod
    def _evidence_only(cls, value: bool) -> bool:
        if not value:
            raise ValueError("shadow sessions must remain evidence-only")
        return value

    def canonical_json(self) -> str:
        return canonical_json(self)


class RuntimeDecision(FrozenContract):
    """Immutable representation of a supplied runtime decision."""

    value: AssessmentValue
    rationale: str | None = None
    source_timestamp: datetime

    @field_validator("source_timestamp")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("source_timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)


class AIOSAssessment(FrozenContract):
    """Immutable analytical assessment supplied by an AIOS observer."""

    value: AssessmentValue
    rationale: str | None = None
    assessed_at: datetime

    @field_validator("assessed_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("assessed_at must be timezone-aware")
        return value.astimezone(timezone.utc)


class DecisionSnapshot(FrozenContract):
    """One runtime/AIOS comparison bound to a common evidence reference."""

    snapshot_id: str
    evidence_id: str
    evidence_digest: str
    sequence_id: int = Field(ge=0)
    runtime: RuntimeDecision
    aios: AIOSAssessment

    @field_validator("snapshot_id", "evidence_id", mode="before")
    @classmethod
    def _identifier(cls, value: str, info: Any) -> str:
        return validate_identifier_segment(value, field_name=info.field_name)

    @field_validator("evidence_digest")
    @classmethod
    def _digest(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("evidence_digest must be a SHA-256 hex digest")
        return normalized

    @model_validator(mode="after")
    def _consistent(self) -> "DecisionSnapshot":
        if self.runtime.source_timestamp > self.aios.assessed_at:
            raise ValueError("AIOS assessment cannot precede runtime decision")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)


class ComparisonArtifact(FrozenContract):
    """Deterministic result of comparing one decision snapshot."""

    snapshot_id: str
    evidence_id: str
    evidence_digest: str
    classification: ComparisonClassification
    runtime_value: AssessmentValue
    aios_value: AssessmentValue
    reason: str

    def canonical_json(self) -> str:
        return canonical_json(self)


class ShadowReport(FrozenContract):
    """Immutable aggregate of controlled comparison artifacts."""

    session: ShadowSession
    snapshots: tuple[DecisionSnapshot, ...] = ()
    artifacts: tuple[ComparisonArtifact, ...] = ()
    agreement_count: int = Field(ge=0)
    disagreement_count: int = Field(ge=0)
    indeterminate_count: int = Field(ge=0)

    @field_validator("artifacts")
    @classmethod
    def _ordered(cls, value: tuple[ComparisonArtifact, ...]) -> tuple[ComparisonArtifact, ...]:
        if tuple(item.snapshot_id for item in value) != tuple(sorted(item.snapshot_id for item in value)):
            raise ValueError("shadow artifacts must be deterministically ordered")
        return value

    @field_validator("snapshots")
    @classmethod
    def _ordered_snapshots(cls, value: tuple[DecisionSnapshot, ...]) -> tuple[DecisionSnapshot, ...]:
        if tuple(item.snapshot_id for item in value) != tuple(sorted(item.snapshot_id for item in value)):
            raise ValueError("decision snapshots must be deterministically ordered")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "ShadowReport":
        if tuple(item.snapshot_id for item in self.snapshots) != tuple(item.snapshot_id for item in self.artifacts):
            raise ValueError("shadow snapshots and artifacts are misaligned")
        for snapshot, artifact in zip(self.snapshots, self.artifacts):
            if (
                snapshot.evidence_id != artifact.evidence_id
                or snapshot.evidence_digest != artifact.evidence_digest
                or snapshot.runtime.value != artifact.runtime_value
                or snapshot.aios.value != artifact.aios_value
            ):
                raise ValueError("shadow artifact does not match its decision snapshot")
        counts = {
            ComparisonClassification.AGREEMENT: self.agreement_count,
            ComparisonClassification.DISAGREEMENT: self.disagreement_count,
            ComparisonClassification.INDETERMINATE: self.indeterminate_count,
        }
        actual = {classification: 0 for classification in counts}
        for artifact in self.artifacts:
            actual[artifact.classification] += 1
        if actual != counts:
            raise ValueError("shadow report classification counts are inconsistent")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
