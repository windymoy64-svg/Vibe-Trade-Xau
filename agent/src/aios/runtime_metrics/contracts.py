"""Immutable, evidence-only decision evaluation metrics contracts."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import Field, field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract, validate_identifier_segment
from src.aios.provenance.serialization import canonical_json
from src.aios.runtime_shadow.contracts import ShadowReport


class DistributionDimension(str, Enum):
    ADAPTER = "adapter"
    RUNTIME = "runtime"
    ASSESSMENT_VALUE = "assessment-value"
    CLASSIFICATION = "classification"


class MetricsSession(FrozenContract):
    """Immutable evaluation session bound to an exact approved report set."""

    session_id: str
    report_set_digest: str
    opened_at: datetime
    report_count: int = Field(ge=0)
    execution_authority: str = "existing-runtime"
    evidence_only: bool = True

    @field_validator("session_id", mode="before")
    @classmethod
    def _session_id(cls, value: str) -> str:
        return validate_identifier_segment(value, field_name="session_id")

    @field_validator("report_set_digest")
    @classmethod
    def _digest(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("report_set_digest must be a SHA-256 hex digest")
        return normalized

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
            raise ValueError("metrics sessions must retain existing-runtime authority")
        return value

    @field_validator("evidence_only")
    @classmethod
    def _evidence_only(cls, value: bool) -> bool:
        if not value:
            raise ValueError("metrics sessions must remain evidence-only")
        return value


class MetricDistribution(FrozenContract):
    """Count and floor-ratio for one deterministic distribution bucket."""

    dimension: DistributionDimension
    key: str
    count: int = Field(ge=0)
    total: int = Field(ge=0)
    ratio: int = Field(ge=0, le=100)

    @field_validator("key")
    @classmethod
    def _key(cls, value: str) -> str:
        return validate_identifier_segment(value, field_name="distribution key")

    @model_validator(mode="after")
    def _consistent(self) -> "MetricDistribution":
        if self.count > self.total or self.ratio != (self.count * 100 // self.total if self.total else 0):
            raise ValueError("metric distribution values are inconsistent")
        return self


class TrendPoint(FrozenContract):
    """Deterministic summary point for one approved shadow report."""

    session_id: str
    opened_at: datetime
    adapter_id: str
    runtime_identity: str
    total_count: int = Field(ge=0)
    agreement_count: int = Field(ge=0)
    disagreement_count: int = Field(ge=0)
    indeterminate_count: int = Field(ge=0)
    agreement_ratio: int = Field(ge=0, le=100)

    @field_validator("session_id", "adapter_id", "runtime_identity", mode="before")
    @classmethod
    def _identifier(cls, value: str, info: Any) -> str:
        return validate_identifier_segment(value, field_name=info.field_name)

    @field_validator("opened_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("opened_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _consistent(self) -> "TrendPoint":
        if self.agreement_count + self.disagreement_count + self.indeterminate_count != self.total_count:
            raise ValueError("trend counts do not sum to total")
        expected = self.agreement_count * 100 // self.total_count if self.total_count else 0
        if self.agreement_ratio != expected:
            raise ValueError("trend agreement ratio is inconsistent")
        return self


class TrendSummary(FrozenContract):
    """Ordered trend projection and endpoint deltas."""

    points: tuple[TrendPoint, ...] = ()
    agreement_delta: int = 0
    disagreement_delta: int = 0
    indeterminate_delta: int = 0

    @field_validator("points")
    @classmethod
    def _ordered(cls, value: tuple[TrendPoint, ...]) -> tuple[TrendPoint, ...]:
        if tuple((item.opened_at, item.session_id) for item in value) != tuple(
            sorted((item.opened_at, item.session_id) for item in value)
        ):
            raise ValueError("trend points must be canonically ordered")
        return value


class DecisionMetricsReport(FrozenContract):
    """Immutable aggregate of approved shadow-report decision metrics."""

    session: MetricsSession
    source_reports: tuple[ShadowReport, ...] = ()
    total_count: int = Field(ge=0)
    agreement_count: int = Field(ge=0)
    disagreement_count: int = Field(ge=0)
    indeterminate_count: int = Field(ge=0)
    agreement_ratio: int = Field(ge=0, le=100)
    disagreement_ratio: int = Field(ge=0, le=100)
    indeterminate_ratio: int = Field(ge=0, le=100)
    coverage_count: int = Field(ge=0)
    coverage_ratio: int = Field(ge=0, le=100)
    distributions: tuple[MetricDistribution, ...] = ()
    trends: TrendSummary = TrendSummary()

    @field_validator("source_reports")
    @classmethod
    def _ordered_reports(cls, value: tuple[ShadowReport, ...]) -> tuple[ShadowReport, ...]:
        if tuple((item.session.opened_at, item.session.session_id) for item in value) != tuple(
            sorted((item.session.opened_at, item.session.session_id) for item in value)
        ):
            raise ValueError("source reports must be canonically ordered")
        return value

    @field_validator("distributions")
    @classmethod
    def _ordered_distributions(cls, value: tuple[MetricDistribution, ...]) -> tuple[MetricDistribution, ...]:
        keys = tuple((item.dimension.value, item.key) for item in value)
        if keys != tuple(sorted(keys)):
            raise ValueError("metric distributions must be canonically ordered")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "DecisionMetricsReport":
        counts = self.agreement_count + self.disagreement_count + self.indeterminate_count
        if counts != self.total_count or self.coverage_count != self.agreement_count + self.disagreement_count:
            raise ValueError("metrics aggregate counts are inconsistent")
        for count, ratio in (
            (self.agreement_count, self.agreement_ratio),
            (self.disagreement_count, self.disagreement_ratio),
            (self.indeterminate_count, self.indeterminate_ratio),
            (self.coverage_count, self.coverage_ratio),
        ):
            if ratio != (count * 100 // self.total_count if self.total_count else 0):
                raise ValueError("metrics ratio is inconsistent")
        if len(self.source_reports) != self.session.report_count:
            raise ValueError("metrics report count does not match session")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
