"""Level 21 acceptance tests for evidence-only decision evaluation metrics."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.aios.runtime_metrics import DecisionMetricsEngine, DistributionDimension
from src.aios.runtime_shadow import (
    AIOSAssessment,
    AssessmentValue,
    DecisionSnapshot,
    RuntimeDecision,
    ShadowComparisonEngine,
    build_shadow_session,
)

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


def _snapshot(index: int, runtime: AssessmentValue, aios: AssessmentValue) -> DecisionSnapshot:
    return DecisionSnapshot(
        snapshot_id=f"metric-snapshot-{index}", evidence_id=f"metric-evidence-{index}",
        evidence_digest=f"{index:064x}", sequence_id=index,
        runtime=RuntimeDecision(value=runtime, source_timestamp=NOW + timedelta(minutes=index)),
        aios=AIOSAssessment(value=aios, assessed_at=NOW + timedelta(minutes=index, seconds=1)),
    )


def _shadow_report(
    name: str,
    opened_at: datetime,
    adapter: str,
    runtime_identity: str,
    snapshots: tuple[DecisionSnapshot, ...],
):  # type: ignore[no-untyped-def]
    session = build_shadow_session(runtime_identity, adapter, opened_at, snapshots)
    return ShadowComparisonEngine(session).compare(snapshots)


def _reports():  # type: ignore[no-untyped-def]
    first = _shadow_report(
        "first", NOW, "adapter-alpha", "runtime-one",
        (
            _snapshot(1, AssessmentValue.APPROVE, AssessmentValue.APPROVE),
            _snapshot(2, AssessmentValue.DENY, AssessmentValue.APPROVE),
        ),
    )
    second = _shadow_report(
        "second", NOW + timedelta(hours=1), "adapter-beta", "runtime-two",
        (
            _snapshot(3, AssessmentValue.HOLD, AssessmentValue.HOLD),
            _snapshot(4, AssessmentValue.UNKNOWN, AssessmentValue.DENY),
        ),
    )
    return first, second


def test_metrics_aggregation_and_ratios() -> None:
    report = DecisionMetricsEngine().evaluate(_reports(), opened_at=NOW + timedelta(days=1))
    assert report.total_count == 4
    assert report.agreement_count == 2
    assert report.disagreement_count == 1
    assert report.indeterminate_count == 1
    assert report.agreement_ratio == 50
    assert report.disagreement_ratio == 25
    assert report.indeterminate_ratio == 25
    assert report.session.report_count == 2
    assert report.session.execution_authority == "existing-runtime"
    assert report.session.evidence_only is True


def test_coverage_calculation_for_populated_and_empty_sets() -> None:
    engine = DecisionMetricsEngine()
    populated = engine.evaluate(_reports(), opened_at=NOW)
    empty = engine.evaluate((), opened_at=NOW)
    assert populated.coverage_count == 3
    assert populated.coverage_ratio == 75
    assert empty.total_count == 0
    assert empty.coverage_count == 0
    assert empty.coverage_ratio == 0


def test_distribution_analysis_by_all_dimensions() -> None:
    report = DecisionMetricsEngine().evaluate(_reports(), opened_at=NOW)
    indexed = {(item.dimension, item.key): (item.count, item.ratio) for item in report.distributions}
    assert indexed[(DistributionDimension.ADAPTER, "adapter-alpha")] == (2, 50)
    assert indexed[(DistributionDimension.ADAPTER, "adapter-beta")] == (2, 50)
    assert indexed[(DistributionDimension.RUNTIME, "runtime-one")] == (2, 50)
    assert indexed[(DistributionDimension.RUNTIME, "runtime-two")] == (2, 50)
    assert indexed[(DistributionDimension.ASSESSMENT_VALUE, "approve")] == (2, 50)
    assert indexed[(DistributionDimension.ASSESSMENT_VALUE, "hold")] == (1, 25)
    assert indexed[(DistributionDimension.CLASSIFICATION, "agreement")] == (2, 50)
    assert indexed[(DistributionDimension.CLASSIFICATION, "indeterminate")] == (1, 25)


def test_trend_summary_is_deterministic_and_canonically_ordered() -> None:
    reports = _reports()
    engine = DecisionMetricsEngine()
    first = engine.evaluate(reports, opened_at=NOW + timedelta(days=1))
    reversed_result = engine.evaluate(reversed(reports), opened_at=NOW + timedelta(days=1))
    assert first.canonical_json() == reversed_result.canonical_json()
    assert tuple(item.runtime_identity for item in first.trends.points) == ("runtime-one", "runtime-two")
    assert first.trends.agreement_delta == 0
    assert first.trends.disagreement_delta == -1
    assert first.trends.indeterminate_delta == 1


def test_replay_consistency_and_canonical_report_generation() -> None:
    engine = DecisionMetricsEngine()
    report = engine.evaluate(_reports(), opened_at=NOW + timedelta(days=1))
    replayed = engine.replay(report)
    assert replayed.canonical_json() == report.canonical_json()
    assert replayed.digest == report.digest
    assert len(report.digest) == 64
    assert len(report.session.report_set_digest) == 64
    with pytest.raises(ValidationError):
        report.total_count = 99  # type: ignore[misc]


def test_duplicate_approved_reports_and_artifacts_fail_closed() -> None:
    first, second = _reports()
    engine = DecisionMetricsEngine()
    with pytest.raises(ValueError, match="duplicate shadow report sessions"):
        engine.evaluate((first, first), opened_at=NOW)
    duplicate_artifact_report = second.model_copy(update={
        "session": second.session.model_copy(update={"session_id": "shadow-distinct"}),
        "snapshots": tuple(item.model_copy(update={"snapshot_id": f"copy-{item.snapshot_id}"}) for item in second.snapshots),
        "artifacts": tuple(item.model_copy(update={"snapshot_id": first.artifacts[index].snapshot_id}) for index, item in enumerate(second.artifacts)),
    })
    with pytest.raises(ValueError, match="duplicate shadow comparison artifacts"):
        engine.evaluate((first, duplicate_artifact_report), opened_at=NOW)


def test_metrics_reject_naive_session_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        DecisionMetricsEngine().evaluate(_reports(), opened_at=datetime(2026, 8, 2, 12, 0))


def test_level21_import_boundary_and_no_authority_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aios" / "runtime_metrics"
    allowed = (
        "src.aios.contracts.identifiers", "src.aios.provenance",
        "src.aios.runtime_shadow", "src.aios.runtime_metrics",
    )
    forbidden_import_parts = {
        "agent", "swarm", "live", "tools", "providers", "trading", "frontend", "api",
        "deployments", "experiments", "broker", "exchange", "scheduler", "migration",
    }
    forbidden_api_names = {
        "execute", "trade", "submit_order", "place_order", "schedule", "persist", "migrate",
        "enforce", "sign", "transfer_authority", "mutate_runtime", "recommend", "cutover", "act",
    }
    violations: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
                if node.module.startswith("src.") and not node.module.startswith(allowed):
                    violations.append(f"{path.name}: unapproved AIOS import {node.module}")
            for name in names:
                if forbidden_import_parts.intersection(name.split(".")):
                    violations.append(f"{path.name}: forbidden import {name}")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden_api_names:
                violations.append(f"{path.name}: forbidden API {node.name}")
    assert violations == []
