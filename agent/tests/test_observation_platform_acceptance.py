"""Phase 10 acceptance tests for the runtime observation platform."""
from __future__ import annotations

import ast
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.aios.observation import (
    ObservationOrchestrator,
    ObservationSession,
    ObservationSessionLifecycle,
    ObservationSource,
    ObservationSourceKind,
    SourceSubmission,
    aggregate_metrics,
    build_dashboard,
    build_evidence_pipeline,
    validate_session_transition,
)
from src.aios.provenance.authenticity import IssuerIdentity, RepositoryTrustedIssuerPolicy
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.verification_manifest import VerificationManifest
from src.aios.runtime.health import HealthState

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def _evidence(evidence_id: str, observed_at: datetime = NOW) -> EvidenceRecord:
    unsealed = EvidenceRecord.model_construct(
        evidence_id=evidence_id,
        evidence_type="runtime-observation",
        issuer_id="phase10-observer",
        observed_at=observed_at,
        subject_digest="a" * 64,
        references=(),
        attributes={"scope": "phase-10"},
        expected_digest="",
    )
    digest = hashlib.sha256(unsealed.canonical_json().encode("utf-8")).hexdigest()
    return EvidenceRecord(**unsealed.model_dump(exclude={"expected_digest"}), expected_digest=digest)


def _policy() -> RepositoryTrustedIssuerPolicy:
    return RepositoryTrustedIssuerPolicy(
        policy_id="phase10-policy",
        version=1,
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        issuers=(
            IssuerIdentity(
                issuer_id="phase10-observer",
                display_name="Phase Ten Observer",
                trust_domain="repository",
                trusted=True,
            ),
        ),
    )


def _manifest(evidence_id: str, *, verified_at: datetime = NOW) -> VerificationManifest:
    return VerificationManifest.create(_evidence(evidence_id, verified_at), _policy(), verified_at=verified_at)


def _source(source_id: str = "runtime-observer", *, health: HealthState = HealthState.HEALTHY) -> ObservationSource:
    return ObservationSource(source_id=source_id, kind=ObservationSourceKind.RUNTIME, health=health)



def test_observation_session_lifecycle() -> None:
    orchestrator = ObservationOrchestrator()
    opened = orchestrator.open_session((_source(),), opened_at=NOW)
    assert opened.lifecycle == ObservationSessionLifecycle.OPENED
    assert opened.execution_authority == "existing-runtime"
    pipeline = build_evidence_pipeline((("runtime-observer", _manifest("evidence-one"), 12),))
    collecting = opened.transition_to(ObservationSessionLifecycle.COLLECTING, pipeline=pipeline)
    sealed = collecting.transition_to(
        ObservationSessionLifecycle.SEALED,
        pipeline=pipeline,
        sealed_at=NOW + timedelta(seconds=5),
    )
    archived = sealed.transition_to(ObservationSessionLifecycle.ARCHIVED)
    assert archived.lifecycle == ObservationSessionLifecycle.ARCHIVED
    with pytest.raises(ValueError, match="invalid observation session transition"):
        validate_session_transition(ObservationSessionLifecycle.OPENED, ObservationSessionLifecycle.SEALED)


def test_evidence_pipeline_ordering_is_deterministic() -> None:
    later = _manifest("evidence-b", verified_at=NOW + timedelta(seconds=2))
    earlier = _manifest("evidence-a", verified_at=NOW + timedelta(seconds=1))
    pipeline = build_evidence_pipeline((("source-z", later, 20), ("source-a", earlier, 10)))
    assert pipeline.evidence_ids == ("evidence-a", "evidence-b")
    assert [entry.sequence for entry in pipeline.entries] == [0, 1]
    assert pipeline.canonical_json() == build_evidence_pipeline(
        (("source-a", earlier, 10), ("source-z", later, 20))
    ).canonical_json()


def test_unverified_manifest_is_rejected_by_pipeline() -> None:
    bad = _manifest("evidence-bad").model_copy(
        update={"authentic": False, "verification_reason": "issuer is not trusted"}
    )
    with pytest.raises(ValueError, match="verified manifests only"):
        build_evidence_pipeline((("runtime-observer", bad, 1),))


def test_session_identifiers_are_deterministic() -> None:
    pipeline = build_evidence_pipeline((("runtime-observer", _manifest("evidence-one"), 5),))
    first = ObservationSession.create(
        lifecycle=ObservationSessionLifecycle.SEALED,
        opened_at=NOW,
        sources=(_source(),),
        pipeline=pipeline,
        sealed_at=NOW + timedelta(seconds=1),
    )
    second = ObservationSession.create(
        lifecycle=ObservationSessionLifecycle.SEALED,
        opened_at=NOW,
        sources=(_source(),),
        pipeline=pipeline,
        sealed_at=NOW + timedelta(seconds=1),
    )
    assert first.session_id == second.session_id
    assert first.digest == second.digest
    with pytest.raises(ValidationError):
        first.lifecycle = ObservationSessionLifecycle.ARCHIVED  # type: ignore[misc]



def test_observation_metrics_aggregation() -> None:
    session = ObservationOrchestrator().coordinate(
        (
            SourceSubmission(
                source=_source("alpha", health=HealthState.HEALTHY),
                manifests=(_manifest("evidence-one"),),
                verification_latencies_ms=(10,),
            ),
            SourceSubmission(
                source=_source("beta", health=HealthState.DEGRADED),
                manifests=(_manifest("evidence-two", verified_at=NOW + timedelta(seconds=1)),),
                verification_latencies_ms=(30,),
            ),
        ),
        opened_at=NOW,
        sealed_at=NOW + timedelta(seconds=3),
    )
    metrics = aggregate_metrics(session, replay_results=(True, True, False), evidence_expected=2)
    assert metrics.average_verification_latency_ms == 20
    assert metrics.max_verification_latency_ms == 30
    assert metrics.replay_success_rate == 66
    assert metrics.evidence_completeness_rate == 100
    assert metrics.observer_health == HealthState.DEGRADED
    assert metrics.healthy_source_ratio == 50
    assert metrics.authoritative is False


def test_dashboard_model_consistency() -> None:
    session = ObservationOrchestrator().coordinate(
        (SourceSubmission(
            source=_source(),
            manifests=(_manifest("evidence-one"),),
            verification_latencies_ms=(8,),
        ),),
        opened_at=NOW,
        sealed_at=NOW + timedelta(seconds=2),
    )
    dashboard = build_dashboard(session)
    assert dashboard.session_id == session.session_id
    assert dashboard.readiness is True
    assert dashboard.authenticity_verified is True
    assert dashboard.provenance_complete is True
    assert dashboard.verification_count == 1
    assert dashboard.verified_count == 1
    assert dashboard.execution_authority == "existing-runtime"
    assert dashboard.canonical_json() == build_dashboard(session).canonical_json()


def test_observation_platform_import_boundary() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aios" / "observation"
    forbidden = {
        "agent", "swarm", "live", "tools", "providers", "trading", "frontend",
        "api", "deployments", "experiments", "execution", "scheduler", "broker",
        "exchange", "strategy", "position", "order", "risk",
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
            for name in names:
                parts = name.split(".")
                if parts[0] == "src" and len(parts) > 1 and parts[1] in forbidden:
                    violations.append(f"{path.name}: {name}")
    assert violations == []


def test_orchestrator_has_no_execution_capability() -> None:
    orchestrator = ObservationOrchestrator()
    assert orchestrator.mode == "observation-only"
    assert orchestrator.execution_authority == "existing-runtime"
    assert orchestrator.executable is False
    assert orchestrator.authoritative is False
    assert not hasattr(orchestrator, "execute")
    assert not hasattr(orchestrator, "trade")
    assert not hasattr(orchestrator, "submit_order")
