"""Deterministic metrics aggregation from approved Shadow Reports."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone

from src.aios.provenance.serialization import canonical_json
from src.aios.runtime_shadow.contracts import ComparisonClassification, ShadowReport
from src.aios.runtime_metrics.contracts import (
    DecisionMetricsReport,
    DistributionDimension,
    MetricDistribution,
    MetricsSession,
    TrendPoint,
    TrendSummary,
)


def _ratio(count: int, total: int) -> int:
    return count * 100 // total if total else 0


class DecisionMetricsEngine:
    """Aggregate approved shadow evidence without recommendation or action."""

    read_only = True
    execution_authority = "existing-runtime"
    evidence_only = True

    def evaluate(self, reports: Iterable[ShadowReport], *, opened_at: datetime) -> DecisionMetricsReport:
        source_reports = tuple(sorted(reports, key=lambda item: (item.session.opened_at, item.session.session_id)))
        self._validate_reports(source_reports)
        if opened_at.tzinfo is None or opened_at.utcoffset() is None:
            raise ValueError("opened_at must be timezone-aware")
        opened_at = opened_at.astimezone(timezone.utc)
        report_set_digest = _report_set_digest(source_reports)
        session_content = canonical_json({"opened_at": opened_at.isoformat(), "report_set_digest": report_set_digest})
        session = MetricsSession(
            session_id=f"metrics-{hashlib.sha256(session_content.encode('utf-8')).hexdigest()[:32]}",
            report_set_digest=report_set_digest, opened_at=opened_at, report_count=len(source_reports),
        )
        artifacts = tuple(artifact for report in source_reports for artifact in report.artifacts)
        total = len(artifacts)
        counts = Counter(item.classification for item in artifacts)
        coverage = counts[ComparisonClassification.AGREEMENT] + counts[ComparisonClassification.DISAGREEMENT]
        distributions = self._distributions(source_reports, artifacts, total)
        trends = TrendSummary(points=tuple(self._trend_point(report) for report in source_reports))
        if trends.points:
            first, last = trends.points[0], trends.points[-1]
            trends = TrendSummary(
                points=trends.points,
                agreement_delta=last.agreement_ratio - first.agreement_ratio,
                disagreement_delta=last.disagreement_count - first.disagreement_count,
                indeterminate_delta=last.indeterminate_count - first.indeterminate_count,
            )
        return DecisionMetricsReport(
            session=session, source_reports=source_reports, total_count=total,
            agreement_count=counts[ComparisonClassification.AGREEMENT],
            disagreement_count=counts[ComparisonClassification.DISAGREEMENT],
            indeterminate_count=counts[ComparisonClassification.INDETERMINATE],
            agreement_ratio=_ratio(counts[ComparisonClassification.AGREEMENT], total),
            disagreement_ratio=_ratio(counts[ComparisonClassification.DISAGREEMENT], total),
            indeterminate_ratio=_ratio(counts[ComparisonClassification.INDETERMINATE], total),
            coverage_count=coverage, coverage_ratio=_ratio(coverage, total), distributions=distributions, trends=trends,
        )

    def replay(self, report: DecisionMetricsReport) -> DecisionMetricsReport:
        return self.evaluate(report.source_reports, opened_at=report.session.opened_at)

    @staticmethod
    def _validate_reports(reports: tuple[ShadowReport, ...]) -> None:
        sessions = tuple(item.session.session_id for item in reports)
        if len(set(sessions)) != len(sessions):
            raise ValueError("duplicate shadow report sessions are not permitted")
        report_digests = tuple(item.digest for item in reports)
        if len(set(report_digests)) != len(report_digests):
            raise ValueError("duplicate shadow reports are not permitted")
        artifact_ids = [artifact.snapshot_id for report in reports for artifact in report.artifacts]
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ValueError("duplicate shadow comparison artifacts are not permitted")

    @staticmethod
    def _distributions(reports: tuple[ShadowReport, ...], artifacts: tuple, total: int) -> tuple[MetricDistribution, ...]:
        entries: list[MetricDistribution] = []
        dimensions: tuple[tuple[DistributionDimension, Counter[str]], ...] = (
            (DistributionDimension.ADAPTER, Counter(report.session.adapter_id for report in reports for _ in report.artifacts)),
            (DistributionDimension.RUNTIME, Counter(report.session.runtime_identity for report in reports for _ in report.artifacts)),
            (DistributionDimension.ASSESSMENT_VALUE, Counter(item.aios_value.value for item in artifacts)),
            (DistributionDimension.CLASSIFICATION, Counter(item.classification.value for item in artifacts)),
        )
        for dimension, counter in dimensions:
            for key, count in sorted(counter.items()):
                entries.append(MetricDistribution(dimension=dimension, key=key, count=count, total=total, ratio=_ratio(count, total)))
        return tuple(sorted(entries, key=lambda item: (item.dimension.value, item.key)))

    @staticmethod
    def _trend_point(report: ShadowReport) -> TrendPoint:
        total = len(report.artifacts)
        agreement = report.agreement_count
        return TrendPoint(
            session_id=report.session.session_id, opened_at=report.session.opened_at,
            adapter_id=report.session.adapter_id, runtime_identity=report.session.runtime_identity,
            total_count=total, agreement_count=agreement,
            disagreement_count=report.disagreement_count, indeterminate_count=report.indeterminate_count,
            agreement_ratio=_ratio(agreement, total),
        )


def _report_set_digest(reports: tuple[ShadowReport, ...]) -> str:
    return hashlib.sha256(canonical_json(reports).encode("utf-8")).hexdigest()
