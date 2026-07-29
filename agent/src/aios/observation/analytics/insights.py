"""Policy, replay, and health insights derived from approved evidence."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from src.aios.observation.analytics.aggregation import _percentage
from src.aios.observation.analytics.contracts import (
    AnalyticsHealthReport, HistoricalReplayComparison, InsightHealth,
    PolicyComplianceSummary, PolicyInsights, ReplayAnalytics, ReplayOutcome,
)
from src.aios.observation.archive.verification import ArchiveVerificationResult
from src.aios.observation.dashboard import ObservationDashboard
from src.aios.observation.session import ObservationSession
from src.aios.provenance.verification_manifest import VerificationManifest


def summarize_policy_insights(
    manifests: Iterable[VerificationManifest], dashboards: Iterable[ObservationDashboard],
) -> PolicyInsights:
    items = tuple(manifests)
    dashboard_items = tuple(dashboards)
    groups: dict[tuple[str, int, str], list[VerificationManifest]] = defaultdict(list)
    for item in items:
        groups[(item.policy_id, item.policy_version, item.policy_digest)].append(item)
    policies = tuple(PolicyComplianceSummary(
        policy_id=key[0], policy_version=key[1], policy_digest=key[2],
        verification_count=len(group), compliant_count=sum(m.integrity_verified and m.authentic for m in group),
        compliance_rate=_percentage(sum(m.integrity_verified and m.authentic for m in group), len(group)),
    ) for key, group in sorted(groups.items()))
    integrity = sum(item.integrity_verified for item in items)
    authentic = sum(item.authentic for item in items)
    ready = sum(item.readiness for item in dashboard_items)
    return PolicyInsights(
        policies=policies, verification_count=len(items), integrity_verified_count=integrity,
        authentic_count=authentic, readiness_session_count=len(dashboard_items), ready_session_count=ready,
        compliance_rate=_percentage(sum(m.integrity_verified and m.authentic for m in items), len(items)),
        authenticity_rate=_percentage(authentic, len(items)), readiness_rate=_percentage(ready, len(dashboard_items)),
    )


def aggregate_replay_analytics(
    expected_evidence_ids: Iterable[str], outcomes: Iterable[ReplayOutcome],
) -> ReplayAnalytics:
    expected = tuple(expected_evidence_ids)
    if len(set(expected)) != len(expected):
        raise ValueError("expected replay evidence identifiers must be unique")
    items = tuple(sorted(outcomes, key=lambda item: (item.session_id, item.replayed_at, item.evidence_id)))
    keys = tuple((item.session_id, item.evidence_id, item.replayed_at) for item in items)
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate replay outcomes are not permitted")
    replayed_ids = {item.evidence_id for item in items}
    grouped: dict[str, list[ReplayOutcome]] = defaultdict(list)
    for item in items:
        grouped[item.session_id].append(item)
    comparisons = tuple(HistoricalReplayComparison(
        session_id=session_id, attempts=len(group), successes=sum(item.matched for item in group),
        success_rate=_percentage(sum(item.matched for item in group), len(group)),
    ) for session_id, group in sorted(grouped.items()))
    successes = sum(item.matched for item in items)
    return ReplayAnalytics(
        expected_evidence_count=len(expected), replayed_evidence_count=len(set(expected) & replayed_ids),
        replay_coverage=_percentage(len(set(expected) & replayed_ids), len(expected)),
        replay_attempts=len(items), replay_successes=successes,
        replay_success_rate=_percentage(successes, len(items)), comparisons=comparisons,
    )


def build_health_report(
    sessions: Iterable[ObservationSession], dashboards: Iterable[ObservationDashboard],
    archive: ArchiveVerificationResult,
) -> AnalyticsHealthReport:
    session_items = tuple(sessions)
    dashboard_items = tuple(dashboards)
    source_ids = {source.source_id for session in session_items for source in session.sources}
    healthy_ids = {source.source_id for session in session_items for source in session.sources if source.healthy}
    verification_count = sum(item.verification_count for item in dashboard_items)
    verified = sum(item.verified_count for item in dashboard_items)
    verification_health = (
        InsightHealth.UNKNOWN if verification_count == 0 else
        InsightHealth.HEALTHY if verified == verification_count else InsightHealth.DEGRADED
    )
    overall = (
        InsightHealth.UNKNOWN if not session_items or not source_ids or archive.batch_count == 0 else
        InsightHealth.HEALTHY if archive.archive_valid and verification_health == InsightHealth.HEALTHY
        and len(healthy_ids) == len(source_ids) else InsightHealth.DEGRADED
    )
    return AnalyticsHealthReport(
        session_count=len(session_items), observer_count=len(source_ids), healthy_observer_count=len(healthy_ids),
        observer_coverage=_percentage(len(healthy_ids), len(source_ids)), verification_count=verification_count,
        verified_count=verified, verification_health=verification_health,
        audit_chain_integrity=archive.chain_integrity, archive_valid=archive.archive_valid, overall_health=overall,
    )
