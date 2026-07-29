"""Deterministic end-to-end composition of approved evidence-only layers."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from src.aios.observation.analytics import (
    aggregate_evidence_quality, aggregate_replay_analytics, analyze_session_trends,
    build_analytics_dashboard, build_health_report, summarize_policy_insights,
)
from src.aios.observation.archive import (
    ObservationArchiveEntry, build_archive_batch, build_audit_chain, verify_archive_integrity,
)
from src.aios.observation.dashboard import build_dashboard
from src.aios.observation.integration.contracts import (
    IntegratedSession, IntegrationDashboard, IntegrationHealth, IntegrationPipelineResult,
    IntegrationSessionInput, IntegrationValidation,
)
from src.aios.observation.integration.validation import validate_cross_layer
from src.aios.observation.metrics import aggregate_metrics
from src.aios.observation.orchestrator import ObservationOrchestrator, SourceSubmission
from src.aios.observation.sources import ObservationSource
from src.aios.provenance.verification_manifest import VerificationManifest


def build_integration_pipeline(
    scenarios: Iterable[IntegrationSessionInput], *, batched_at: datetime,
) -> IntegrationPipelineResult:
    """Build and validate the complete evidence pipeline without operational side effects."""
    ordered = tuple(sorted(scenarios, key=lambda item: (item.opened_at, item.scenario_id)))
    if not ordered:
        raise ValueError("integration pipeline requires at least one session scenario")
    if len({item.scenario_id for item in ordered}) != len(ordered):
        raise ValueError("integration scenario identifiers must be unique")
    all_evidence_ids = tuple(item.evidence.evidence_id for scenario in ordered for item in scenario.submissions)
    if len(set(all_evidence_ids)) != len(all_evidence_ids):
        raise ValueError("evidence identifiers must be unique across integration sessions")

    integrated: list[IntegratedSession] = []
    manifests: list[VerificationManifest] = []
    outcomes = []
    for scenario in ordered:
        prepared = tuple(sorted(
            scenario.submissions,
            key=lambda item: (item.verified_at, item.evidence.evidence_id, item.source.source_id),
        ))
        verified = tuple(VerificationManifest.create(
            item.evidence, item.policy, verified_at=item.verified_at
        ) for item in prepared)
        grouped: dict[str, list[tuple[VerificationManifest, int, ObservationSource]]] = {}
        for item, manifest in zip(prepared, verified, strict=True):
            grouped.setdefault(item.source.source_id, []).append((manifest, item.verification_latency_ms, item.source))
        submissions = tuple(SourceSubmission(
            source=values[0][2],
            manifests=tuple(value[0] for value in values),
            verification_latencies_ms=tuple(value[1] for value in values),
        ) for _, values in sorted(grouped.items()))
        session = ObservationOrchestrator().coordinate(
            submissions, opened_at=scenario.opened_at, sealed_at=scenario.sealed_at,
        )
        session_outcomes = tuple(item for item in scenario.replay_outcomes)
        metrics = aggregate_metrics(
            session, replay_results=(item.matched for item in session_outcomes),
            evidence_expected=scenario.evidence_expected,
        )
        integrated.append(IntegratedSession(
            scenario_id=scenario.scenario_id, session=session, metrics=metrics,
            dashboard=build_dashboard(session),
            archive_entry=ObservationArchiveEntry.create(session, archived_at=scenario.archived_at),
        ))
        manifests.extend(verified)
        outcomes.extend(session_outcomes)

    sessions = tuple(integrated)
    archive_batch = build_archive_batch(
        (item.archive_entry for item in sessions), batched_at=batched_at,
    )
    audit_chain = build_audit_chain((archive_batch,))
    archive_verification = verify_archive_integrity((archive_batch,), audit_chain)
    raw_sessions = tuple(item.session for item in sessions)
    metrics = tuple(item.metrics for item in sessions)
    observation_dashboards = tuple(item.dashboard for item in sessions)
    quality = aggregate_evidence_quality(raw_sessions, metrics)
    trends = analyze_session_trends(raw_sessions, {item.session_id: metric for item, metric in zip(raw_sessions, metrics)})
    policy = summarize_policy_insights(manifests, observation_dashboards)
    replay = aggregate_replay_analytics(all_evidence_ids, outcomes)
    health = build_health_report(raw_sessions, observation_dashboards, archive_verification)
    analytics = build_analytics_dashboard(quality, trends, policy, replay, health)

    provisional_dashboard = IntegrationDashboard(
        pipeline_health=IntegrationHealth.HEALTHY, session_count=len(sessions),
        evidence_count=len(manifests), verification_count=sum(item.metrics.verification_count for item in sessions),
        archive_entry_count=len(archive_batch.entries), batch_count=1,
        archive_valid=archive_verification.archive_valid,
        audit_chain_integrity=archive_verification.chain_integrity,
        replay_coverage=replay.replay_coverage, invariant_count=0,
    )
    provisional = IntegrationPipelineResult(
        manifests=tuple(manifests), sessions=sessions, archive_batch=archive_batch,
        audit_chain=audit_chain, archive_verification=archive_verification, analytics=analytics,
        validation=IntegrationValidation(valid=True), dashboard=provisional_dashboard,
    )
    validation = validate_cross_layer(provisional)
    dashboard = provisional_dashboard.model_copy(update={
        "pipeline_health": IntegrationHealth.HEALTHY if validation.valid else IntegrationHealth.INVALID,
        "invariant_count": len(validation.findings),
    })
    return provisional.model_copy(update={"validation": validation, "dashboard": dashboard})


def refresh_integration_analytics(result: IntegrationPipelineResult) -> IntegrationPipelineResult:
    """Recompute analytics from captured artifacts; no clock, scheduler, or I/O is used."""
    sessions = tuple(item.session for item in result.sessions)
    metrics = tuple(item.metrics for item in result.sessions)
    dashboards = tuple(item.dashboard for item in result.sessions)
    quality = aggregate_evidence_quality(sessions, metrics)
    trends = analyze_session_trends(sessions, {item.session_id: metric for item, metric in zip(sessions, metrics)})
    policy = summarize_policy_insights(result.manifests, dashboards)
    replay = result.analytics.replay
    health = build_health_report(sessions, dashboards, result.archive_verification)
    analytics = build_analytics_dashboard(quality, trends, policy, replay, health)
    refreshed = result.model_copy(update={"analytics": analytics})
    validation = validate_cross_layer(refreshed)
    dashboard = refreshed.dashboard.model_copy(update={
        "pipeline_health": IntegrationHealth.HEALTHY if validation.valid else IntegrationHealth.INVALID,
        "invariant_count": len(validation.findings), "replay_coverage": replay.replay_coverage,
    })
    return refreshed.model_copy(update={"validation": validation, "dashboard": dashboard})
