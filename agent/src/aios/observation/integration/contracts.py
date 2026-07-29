"""Immutable contracts for Phase 13 evidence-layer integration."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract, validate_identifier_segment
from src.aios.observation.analytics.contracts import EvidenceAnalyticsDashboard, ReplayOutcome
from src.aios.observation.archive.batch import ObservationArchiveBatch
from src.aios.observation.archive.chain import AuditChain
from src.aios.observation.archive.entry import ObservationArchiveEntry
from src.aios.observation.archive.verification import ArchiveVerificationResult
from src.aios.observation.dashboard import ObservationDashboard
from src.aios.observation.metrics import ObservationMetrics
from src.aios.observation.session import ObservationSession
from src.aios.observation.sources import ObservationSource
from src.aios.provenance.authenticity import RepositoryTrustedIssuerPolicy
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.serialization import canonical_json
from src.aios.provenance.verification_manifest import VerificationManifest


class IntegrationHealth(str, Enum):
    HEALTHY = "healthy"
    INVALID = "invalid"


class IntegrationContract(FrozenContract):
    schema_version: int = 1
    authoritative: bool = False
    evidence_only: bool = True
    execution_authority: str = "existing-runtime"

    @model_validator(mode="after")
    def _boundary(self) -> "IntegrationContract":
        if self.schema_version != 1:
            raise ValueError("unsupported integration schema version")
        if self.authoritative or not self.evidence_only or self.execution_authority != "existing-runtime":
            raise ValueError("integration artifacts must remain evidence-only")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)


class EvidenceVerificationInput(FrozenContract):
    evidence: EvidenceRecord
    policy: RepositoryTrustedIssuerPolicy
    source: ObservationSource
    verified_at: datetime
    verification_latency_ms: int = 0

    @field_validator("verified_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("verification timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("verification_latency_ms")
    @classmethod
    def _latency(cls, value: int) -> int:
        if value < 0:
            raise ValueError("verification latency must be non-negative")
        return value


class IntegrationSessionInput(FrozenContract):
    scenario_id: str
    submissions: tuple[EvidenceVerificationInput, ...]
    opened_at: datetime
    sealed_at: datetime
    archived_at: datetime
    evidence_expected: int
    replay_outcomes: tuple[ReplayOutcome, ...] = ()

    @field_validator("scenario_id", mode="before")
    @classmethod
    def _scenario_id(cls, value: str) -> str:
        return validate_identifier_segment(value, field_name="scenario_id")

    @field_validator("opened_at", "sealed_at", "archived_at")
    @classmethod
    def _timestamps(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("integration timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _consistent(self) -> "IntegrationSessionInput":
        if not self.submissions:
            raise ValueError("integration sessions require evidence submissions")
        if not self.opened_at <= self.sealed_at <= self.archived_at:
            raise ValueError("integration timestamps must be chronological")
        if self.evidence_expected < len(self.submissions):
            raise ValueError("expected evidence cannot be less than submitted evidence")
        evidence_ids = tuple(item.evidence.evidence_id for item in self.submissions)
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("integration session evidence must be unique")
        return self


class IntegrationDashboard(IntegrationContract):
    pipeline_health: IntegrationHealth
    session_count: int
    evidence_count: int
    verification_count: int
    archive_entry_count: int
    batch_count: int
    archive_valid: bool
    audit_chain_integrity: bool
    replay_coverage: int
    invariant_count: int


class IntegrationValidation(IntegrationContract):
    valid: bool
    findings: tuple[str, ...] = ()


class IntegratedSession(FrozenContract):
    scenario_id: str
    session: ObservationSession
    metrics: ObservationMetrics
    dashboard: ObservationDashboard
    archive_entry: ObservationArchiveEntry


class IntegrationPipelineResult(IntegrationContract):
    manifests: tuple[VerificationManifest, ...]
    sessions: tuple[IntegratedSession, ...]
    archive_batch: ObservationArchiveBatch
    audit_chain: AuditChain
    archive_verification: ArchiveVerificationResult
    analytics: EvidenceAnalyticsDashboard
    validation: IntegrationValidation
    dashboard: IntegrationDashboard
