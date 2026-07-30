"""Level 20 acceptance tests for controlled evidence-only shadow evaluation."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.aios.runtime_adapter import CanonicalRuntimeAdapter, RuntimeEvent
from src.aios.runtime_shadow import (
    AIOSAssessment,
    AssessmentValue,
    ComparisonClassification,
    DecisionSnapshot,
    RuntimeDecision,
    ShadowComparisonEngine,
    build_shadow_session,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def _evidence(sequence_id: int):  # type: ignore[no-untyped-def]
    event = RuntimeEvent(
        event_id=f"event-{sequence_id}", event_type="decision-observation",
        source_id="runtime-observer", sequence_id=sequence_id,
        occurred_at=NOW + timedelta(seconds=sequence_id), payload={"subject": f"case-{sequence_id}"},
    )
    return CanonicalRuntimeAdapter().adapt(event)


def _snapshot(
    sequence_id: int,
    runtime_value: AssessmentValue,
    aios_value: AssessmentValue,
) -> DecisionSnapshot:
    evidence = _evidence(sequence_id)
    return DecisionSnapshot(
        snapshot_id=f"snapshot-{sequence_id}", evidence_id=evidence.evidence_id,
        evidence_digest=evidence.expected_digest, sequence_id=sequence_id,
        runtime=RuntimeDecision(value=runtime_value, source_timestamp=evidence.observed_at),
        aios=AIOSAssessment(value=aios_value, assessed_at=evidence.observed_at + timedelta(milliseconds=1)),
    )


def _engine(*snapshots: DecisionSnapshot) -> ShadowComparisonEngine:
    session = build_shadow_session("runtime-primary", "canonical-runtime-event", NOW, snapshots)
    return ShadowComparisonEngine(session)


def test_shadow_session_lifecycle_is_immutable_and_deterministic() -> None:
    snapshots = (_snapshot(1, AssessmentValue.APPROVE, AssessmentValue.APPROVE),)
    first = _engine(*snapshots).session
    second = _engine(*snapshots).session
    assert first == second
    assert first.runtime_identity == "runtime-primary"
    assert first.adapter_id == "canonical-runtime-event"
    assert first.opened_at == NOW
    assert first.execution_authority == "existing-runtime"
    assert first.evidence_only is True
    assert len(first.snapshot_set_digest) == 64
    with pytest.raises(ValidationError):
        first.session_id = "changed"  # type: ignore[misc]


def test_decision_comparison_classifies_agreement_disagreement_and_indeterminate() -> None:
    snapshots = (
        _snapshot(1, AssessmentValue.APPROVE, AssessmentValue.APPROVE),
        _snapshot(2, AssessmentValue.APPROVE, AssessmentValue.DENY),
        _snapshot(3, AssessmentValue.UNKNOWN, AssessmentValue.HOLD),
    )
    report = _engine(*snapshots).compare(reversed(snapshots))
    assert tuple(item.classification for item in report.artifacts) == (
        ComparisonClassification.AGREEMENT,
        ComparisonClassification.DISAGREEMENT,
        ComparisonClassification.INDETERMINATE,
    )
    assert report.agreement_count == 1
    assert report.disagreement_count == 1
    assert report.indeterminate_count == 1
    assert tuple(item.snapshot_id for item in report.snapshots) == ("snapshot-1", "snapshot-2", "snapshot-3")


def test_known_hold_values_agree_and_unknown_values_remain_indeterminate() -> None:
    snapshots = (
        _snapshot(1, AssessmentValue.HOLD, AssessmentValue.HOLD),
        _snapshot(2, AssessmentValue.UNKNOWN, AssessmentValue.UNKNOWN),
    )
    report = _engine(*snapshots).compare(snapshots)
    assert report.artifacts[0].classification == ComparisonClassification.AGREEMENT
    assert report.artifacts[1].classification == ComparisonClassification.INDETERMINATE


def test_deterministic_replay_produces_identical_comparison_report() -> None:
    snapshots = (
        _snapshot(2, AssessmentValue.DENY, AssessmentValue.APPROVE),
        _snapshot(1, AssessmentValue.APPROVE, AssessmentValue.APPROVE),
    )
    engine = _engine(*snapshots)
    original = engine.compare(snapshots)
    replayed = engine.replay(original)
    assert replayed.canonical_json() == original.canonical_json()
    assert replayed.digest == original.digest


def test_canonical_report_generation_is_order_independent() -> None:
    snapshots = (
        _snapshot(1, AssessmentValue.APPROVE, AssessmentValue.DENY),
        _snapshot(2, AssessmentValue.DENY, AssessmentValue.DENY),
    )
    engine = _engine(*snapshots)
    first = engine.compare(snapshots)
    second = engine.compare(reversed(snapshots))
    assert first.canonical_json() == second.canonical_json()
    assert first.digest == second.digest
    assert len(first.digest) == 64


def test_cross_layer_evidence_reference_is_preserved() -> None:
    evidence = _evidence(1)
    assert evidence.verify().verified is True
    snapshot = DecisionSnapshot(
        snapshot_id="snapshot-cross-layer", evidence_id=evidence.evidence_id,
        evidence_digest=evidence.expected_digest, sequence_id=1,
        runtime=RuntimeDecision(value=AssessmentValue.APPROVE, source_timestamp=evidence.observed_at),
        aios=AIOSAssessment(value=AssessmentValue.APPROVE, assessed_at=evidence.observed_at),
    )
    artifact = _engine(snapshot).compare((snapshot,)).artifacts[0]
    assert artifact.evidence_id == evidence.evidence_id
    assert artifact.evidence_digest == evidence.expected_digest


def test_invalid_snapshot_and_duplicate_identifiers_fail_closed() -> None:
    evidence = _evidence(1)
    with pytest.raises(ValidationError, match="cannot precede"):
        DecisionSnapshot(
            snapshot_id="snapshot-invalid", evidence_id=evidence.evidence_id,
            evidence_digest=evidence.expected_digest, sequence_id=1,
            runtime=RuntimeDecision(value=AssessmentValue.APPROVE, source_timestamp=NOW),
            aios=AIOSAssessment(value=AssessmentValue.APPROVE, assessed_at=NOW - timedelta(seconds=1)),
        )
    snapshot = _snapshot(1, AssessmentValue.APPROVE, AssessmentValue.APPROVE)
    with pytest.raises(ValueError, match="duplicate"):
        _engine(snapshot).compare((snapshot, snapshot))


def test_replay_rejects_different_shadow_session() -> None:
    snapshot = _snapshot(1, AssessmentValue.APPROVE, AssessmentValue.APPROVE)
    report = _engine(snapshot).compare((snapshot,))
    other = build_shadow_session("runtime-secondary", "canonical-runtime-event", NOW, (snapshot,))
    with pytest.raises(ValueError, match="does not match"):
        ShadowComparisonEngine(other).replay(report)


def test_session_rejects_a_different_snapshot_set() -> None:
    first = _snapshot(1, AssessmentValue.APPROVE, AssessmentValue.APPROVE)
    second = _snapshot(2, AssessmentValue.DENY, AssessmentValue.DENY)
    engine = _engine(first)
    with pytest.raises(ValueError, match="do not match shadow session"):
        engine.compare((second,))


def test_level20_import_boundary_and_no_authority_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aios" / "runtime_shadow"
    allowed = (
        "src.aios.contracts.identifiers", "src.aios.provenance",
        "src.aios.runtime_shadow",
    )
    forbidden_import_parts = {
        "agent", "swarm", "live", "tools", "providers", "trading", "frontend", "api",
        "deployments", "experiments", "broker", "exchange", "scheduler", "migration",
    }
    forbidden_api_names = {
        "execute", "trade", "submit_order", "place_order", "schedule", "persist", "migrate",
        "enforce", "sign", "transfer_authority", "mutate_runtime", "recommend", "cutover",
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
