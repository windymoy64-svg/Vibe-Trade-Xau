"""Immutable contracts for Phase 12 evidence analytics."""
from __future__ import annotations

from enum import Enum

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.provenance.serialization import canonical_json


class InsightHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class AnalyticsContract(FrozenContract):
    """Base invariant shared by all non-authoritative analytics artifacts."""

    schema_version: int = 1
    authoritative: bool = False
    evidence_only: bool = True
    execution_authority: str = "existing-runtime"

    @model_validator(mode="after")
    def _analytics_boundary(self) -> "AnalyticsContract":
        if self.schema_version != 1:
            raise ValueError("unsupported analytics schema version")
        if self.authoritative or not self.evidence_only or self.execution_authority != "existing-runtime":
            raise ValueError("analytics artifacts must remain evidence-only")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)


class EvidenceQualityAnalytics(AnalyticsContract):
    session_count: int
    evidence_expected: int
    evidence_present: int
    completeness_rate: int
    verification_count: int
    average_verification_latency_ms: int
    authentic_count: int
    authenticity_rate: int

    @field_validator(
        "session_count", "evidence_expected", "evidence_present", "completeness_rate",
        "verification_count", "average_verification_latency_ms", "authentic_count", "authenticity_rate",
    )
    @classmethod
    def _metric(cls, value: int, info: object) -> int:
        if value < 0 or (str(getattr(info, "field_name", "")).endswith("rate") and value > 100):
            raise ValueError("evidence analytics metric is outside its valid range")
        return value


class SessionTrendPoint(FrozenContract):
    session_id: str
    opened_at: str
    evidence_completeness_rate: int
    replay_success_rate: int
    healthy_source_ratio: int
    verification_count: int


class EvidenceTrendAnalytics(AnalyticsContract):
    points: tuple[SessionTrendPoint, ...] = ()
    completeness_delta: int = 0
    replay_success_delta: int = 0
    healthy_source_delta: int = 0


class PolicyComplianceSummary(FrozenContract):
    policy_id: str
    policy_version: int
    policy_digest: str
    verification_count: int
    compliant_count: int
    compliance_rate: int


class PolicyInsights(AnalyticsContract):
    policies: tuple[PolicyComplianceSummary, ...] = ()
    verification_count: int
    integrity_verified_count: int
    authentic_count: int
    readiness_session_count: int
    ready_session_count: int
    compliance_rate: int
    authenticity_rate: int
    readiness_rate: int


class ReplayOutcome(FrozenContract):
    session_id: str
    evidence_id: str
    replayed_at: str
    matched: bool


class HistoricalReplayComparison(FrozenContract):
    session_id: str
    attempts: int
    successes: int
    success_rate: int


class ReplayAnalytics(AnalyticsContract):
    expected_evidence_count: int
    replayed_evidence_count: int
    replay_coverage: int
    replay_attempts: int
    replay_successes: int
    replay_success_rate: int
    comparisons: tuple[HistoricalReplayComparison, ...] = ()


class AnalyticsHealthReport(AnalyticsContract):
    session_count: int
    observer_count: int
    healthy_observer_count: int
    observer_coverage: int
    verification_count: int
    verified_count: int
    verification_health: InsightHealth
    audit_chain_integrity: bool
    archive_valid: bool
    overall_health: InsightHealth


class EvidenceAnalyticsDashboard(AnalyticsContract):
    quality: EvidenceQualityAnalytics
    trends: EvidenceTrendAnalytics
    policy: PolicyInsights
    replay: ReplayAnalytics
    health: AnalyticsHealthReport
