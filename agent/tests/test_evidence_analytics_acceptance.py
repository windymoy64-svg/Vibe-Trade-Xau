"""Phase 12 acceptance tests for evidence analytics and policy insights."""
from __future__ import annotations

import ast
import importlib.util
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.aios.observation import aggregate_metrics, build_dashboard
from src.aios.observation.analytics import (
    InsightHealth, ReplayOutcome, aggregate_evidence_quality, aggregate_replay_analytics,
    analyze_session_trends, build_analytics_dashboard, build_health_report, summarize_policy_insights,
)
from src.aios.observation.archive import (
    ObservationArchiveEntry, build_archive_batch, build_audit_chain, verify_archive_integrity,
)

_ARCHIVE_TEST_PATH = Path(__file__).with_name("test_observation_archive_acceptance.py")
_ARCHIVE_SPEC = importlib.util.spec_from_file_location("phase11_acceptance_fixtures", _ARCHIVE_TEST_PATH)
if _ARCHIVE_SPEC is None or _ARCHIVE_SPEC.loader is None:
    raise RuntimeError("unable to load approved Phase 11 acceptance fixtures")
_ARCHIVE_FIXTURES = importlib.util.module_from_spec(_ARCHIVE_SPEC)
_ARCHIVE_SPEC.loader.exec_module(_ARCHIVE_FIXTURES)
NOW = _ARCHIVE_FIXTURES.NOW
_sealed_session = _ARCHIVE_FIXTURES._sealed_session


def _inputs():
    first = _sealed_session("analytics-one", 0)
    second = _sealed_session("analytics-two", 10)
    first_metrics = aggregate_metrics(first, replay_results=(True, False), evidence_expected=2)
    second_metrics = aggregate_metrics(second, replay_results=(True,), evidence_expected=1)
    return (first, second), (first_metrics, second_metrics)


def _archive(sessions):
    entries = tuple(ObservationArchiveEntry.create(
        session, archived_at=NOW + timedelta(hours=index + 1)
    ) for index, session in enumerate(sessions))
    batch = build_archive_batch(entries, batched_at=NOW + timedelta(hours=3))
    return verify_archive_integrity((batch,), build_audit_chain((batch,)))


def test_analytics_aggregation() -> None:
    sessions, metrics = _inputs()
    result = aggregate_evidence_quality(sessions, metrics)
    assert result.session_count == 2
    assert result.evidence_expected == 3
    assert result.evidence_present == 2
    assert result.completeness_rate == 66
    assert result.verification_count == 2
    assert result.average_verification_latency_ms == 1
    assert result.authenticity_rate == 100
    with pytest.raises(ValueError, match="exactly one metrics"):
        aggregate_evidence_quality(sessions, metrics[:1])


def test_trend_determinism() -> None:
    sessions, metrics = _inputs()
    by_session = {item.session_id: item for item in metrics}
    first = analyze_session_trends(sessions, by_session)
    reversed_result = analyze_session_trends(reversed(sessions), by_session)
    assert first == reversed_result
    assert first.points[0].session_id == sessions[0].session_id
    assert first.completeness_delta == 50
    assert first.replay_success_delta == 50
    assert first.canonical_json() == reversed_result.canonical_json()


def test_policy_insight_consistency() -> None:
    sessions, _ = _inputs()
    manifests = tuple(entry.manifest for session in sessions for entry in session.pipeline.entries)
    dashboards = tuple(build_dashboard(session) for session in sessions)
    result = summarize_policy_insights(reversed(manifests), reversed(dashboards))
    assert result.verification_count == 2
    assert result.integrity_verified_count == 2
    assert result.authentic_count == 2
    assert result.compliance_rate == 100
    assert result.authenticity_rate == 100
    assert result.readiness_rate == 100
    assert len(result.policies) == 1
    assert result.policies[0].compliance_rate == 100


def test_replay_analytics_correctness_and_historical_comparison() -> None:
    outcomes = (
        ReplayOutcome(session_id="session-b", evidence_id="evidence-two", replayed_at="2026-07-29T12:02:00+00:00", matched=False),
        ReplayOutcome(session_id="session-a", evidence_id="evidence-one", replayed_at="2026-07-29T12:01:00+00:00", matched=True),
    )
    result = aggregate_replay_analytics(("evidence-one", "evidence-two", "evidence-three"), outcomes)
    assert result.expected_evidence_count == 3
    assert result.replayed_evidence_count == 2
    assert result.replay_coverage == 66
    assert result.replay_attempts == 2
    assert result.replay_successes == 1
    assert result.replay_success_rate == 50
    assert tuple(item.session_id for item in result.comparisons) == ("session-a", "session-b")
    assert result == aggregate_replay_analytics(
        ("evidence-one", "evidence-two", "evidence-three"), reversed(outcomes)
    )


def test_health_report_consistency() -> None:
    sessions, _ = _inputs()
    dashboards = tuple(build_dashboard(session) for session in sessions)
    report = build_health_report(sessions, dashboards, _archive(sessions))
    assert report.session_count == 2
    assert report.verification_count == 2
    assert report.verified_count == 2
    assert report.verification_health == InsightHealth.HEALTHY
    assert report.audit_chain_integrity is True
    assert report.observer_coverage == 0
    assert report.overall_health == InsightHealth.UNKNOWN


def test_analytics_dashboard_is_immutable_and_deterministic() -> None:
    sessions, metrics = _inputs()
    quality = aggregate_evidence_quality(sessions, metrics)
    trends = analyze_session_trends(sessions, {item.session_id: item for item in metrics})
    policy = summarize_policy_insights(
        (entry.manifest for session in sessions for entry in session.pipeline.entries),
        (build_dashboard(session) for session in sessions),
    )
    replay = aggregate_replay_analytics((), ())
    health = build_health_report(sessions, (build_dashboard(item) for item in sessions), _archive(sessions))
    first = build_analytics_dashboard(quality, trends, policy, replay, health)
    second = build_analytics_dashboard(quality, trends, policy, replay, health)
    assert first.canonical_json() == second.canonical_json()
    assert first.execution_authority == "existing-runtime"
    assert first.authoritative is False
    with pytest.raises(ValidationError):
        first.authoritative = True  # type: ignore[misc]


def test_phase12_import_boundary_and_no_execution_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aios" / "observation" / "analytics"
    allowed = (
        "src.aios.contracts.identifiers", "src.aios.provenance.serialization",
        "src.aios.provenance.verification_manifest", "src.aios.observation.analytics",
        "src.aios.observation.archive.verification", "src.aios.observation.dashboard",
        "src.aios.observation.metrics", "src.aios.observation.session",
    )
    forbidden_names = {"execute", "trade", "submit_order", "schedule", "persist", "migrate", "enforce"}
    violations: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("src."):
                if not node.module.startswith(allowed):
                    violations.append(f"{path.name}: {node.module}")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden_names:
                violations.append(f"{path.name}: forbidden API {node.name}")
    assert violations == []
