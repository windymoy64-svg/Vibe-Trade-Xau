"""Deterministic evidence-quality and session-trend aggregation."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from src.aios.observation.analytics.contracts import (
    EvidenceQualityAnalytics, EvidenceTrendAnalytics, SessionTrendPoint,
)
from src.aios.observation.dashboard import build_dashboard
from src.aios.observation.metrics import ObservationMetrics
from src.aios.observation.session import ObservationSession


def _percentage(numerator: int, denominator: int) -> int:
    return numerator * 100 // denominator if denominator > 0 else 0


def aggregate_evidence_quality(
    sessions: Iterable[ObservationSession], metrics: Iterable[ObservationMetrics],
) -> EvidenceQualityAnalytics:
    items = tuple(sessions)
    metric_items = tuple(metrics)
    if len({item.session_id for item in metric_items}) != len(metric_items):
        raise ValueError("duplicate session metrics are not permitted")
    metric_by_session = {item.session_id: item for item in metric_items}
    if set(metric_by_session) != {item.session_id for item in items}:
        raise ValueError("analytics require exactly one metrics artifact per session")
    expected = sum(item.evidence_expected for item in metric_items)
    present = sum(item.evidence_present for item in metric_items)
    verification_count = sum(item.verification_count for item in metric_items)
    latency_total = sum(item.average_verification_latency_ms * item.verification_count for item in metric_items)
    authentic = sum(build_dashboard(item).verified_count for item in items)
    return EvidenceQualityAnalytics(
        session_count=len(items), evidence_expected=expected, evidence_present=present,
        completeness_rate=_percentage(min(present, expected), expected),
        verification_count=verification_count,
        average_verification_latency_ms=(latency_total // verification_count if verification_count else 0),
        authentic_count=authentic, authenticity_rate=_percentage(authentic, verification_count),
    )


def analyze_session_trends(
    sessions: Iterable[ObservationSession], metrics_by_session: Mapping[str, ObservationMetrics],
) -> EvidenceTrendAnalytics:
    ordered = tuple(sorted(sessions, key=lambda item: (item.opened_at, item.session_id)))
    if set(metrics_by_session) != {item.session_id for item in ordered}:
        raise ValueError("trend analytics require exactly one metrics artifact per session")
    points = tuple(SessionTrendPoint(
        session_id=item.session_id, opened_at=item.opened_at.isoformat(),
        evidence_completeness_rate=metrics_by_session[item.session_id].evidence_completeness_rate,
        replay_success_rate=metrics_by_session[item.session_id].replay_success_rate,
        healthy_source_ratio=metrics_by_session[item.session_id].healthy_source_ratio,
        verification_count=metrics_by_session[item.session_id].verification_count,
    ) for item in ordered)
    if not points:
        return EvidenceTrendAnalytics()
    return EvidenceTrendAnalytics(
        points=points,
        completeness_delta=points[-1].evidence_completeness_rate - points[0].evidence_completeness_rate,
        replay_success_delta=points[-1].replay_success_rate - points[0].replay_success_rate,
        healthy_source_delta=points[-1].healthy_source_ratio - points[0].healthy_source_ratio,
    )
