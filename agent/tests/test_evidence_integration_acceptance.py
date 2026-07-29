"""Phase 13 acceptance tests for deterministic evidence-layer integration."""
from __future__ import annotations

import ast
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.aios.observation.analytics import ReplayOutcome
from src.aios.observation.integration import (
    EvidenceVerificationInput, IntegrationHealth, IntegrationSessionInput,
    build_integration_pipeline, refresh_integration_analytics, validate_cross_layer,
)
from src.aios.observation.sources import ObservationSource, ObservationSourceKind
from src.aios.provenance.authenticity import IssuerIdentity, RepositoryTrustedIssuerPolicy
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.runtime.health import HealthState

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def _evidence(evidence_id: str, observed_at: datetime) -> EvidenceRecord:
    unsealed = EvidenceRecord.model_construct(
        evidence_id=evidence_id, evidence_type="runtime-observation", issuer_id="phase13-observer",
        observed_at=observed_at, subject_digest="a" * 64, references=(),
        attributes={"scope": "phase-13"}, expected_digest="",
    )
    return EvidenceRecord(
        **unsealed.model_dump(exclude={"expected_digest"}),
        expected_digest=hashlib.sha256(unsealed.canonical_json().encode()).hexdigest(),
    )


def _policy() -> RepositoryTrustedIssuerPolicy:
    return RepositoryTrustedIssuerPolicy(
        policy_id="phase13-policy", version=1, effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=2), issuers=(IssuerIdentity(
            issuer_id="phase13-observer", display_name="Phase Thirteen Observer",
            trust_domain="repository", trusted=True,
        ),),
    )


def _scenario(index: int, *, replay: bool = True) -> IntegrationSessionInput:
    opened = NOW + timedelta(minutes=index * 10)
    evidence_id = f"phase13-evidence-{index}"
    outcome = (ReplayOutcome(
        session_id=f"scenario-{index}", evidence_id=evidence_id,
        replayed_at=(opened + timedelta(seconds=4)).isoformat(), matched=True,
    ),) if replay else ()
    return IntegrationSessionInput(
        scenario_id=f"scenario-{index}",
        submissions=(EvidenceVerificationInput(
            evidence=_evidence(evidence_id, opened), policy=_policy(),
            source=ObservationSource(
                source_id=f"observer-{index}", kind=ObservationSourceKind.RUNTIME,
                health=HealthState.HEALTHY,
            ), verified_at=opened, verification_latency_ms=index + 1,
        ),),
        opened_at=opened, sealed_at=opened + timedelta(seconds=1),
        archived_at=opened + timedelta(seconds=2), evidence_expected=1,
        replay_outcomes=outcome,
    )


def _build(*scenarios: IntegrationSessionInput):
    return build_integration_pipeline(scenarios, batched_at=NOW + timedelta(days=1))


def test_end_to_end_single_session_pipeline() -> None:
    result = _build(_scenario(0))
    assert len(result.manifests) == 1
    assert len(result.sessions) == 1
    assert result.archive_verification.archive_valid is True
    assert result.audit_chain.verify_integrity() is True
    assert result.analytics.quality.verification_count == 1
    assert result.dashboard.pipeline_health == IntegrationHealth.HEALTHY
    assert result.validation.valid is True


def test_multi_session_integration() -> None:
    result = _build(_scenario(2), _scenario(0), _scenario(1))
    assert tuple(item.scenario_id for item in result.sessions) == ("scenario-0", "scenario-1", "scenario-2")
    assert result.dashboard.session_count == 3
    assert result.dashboard.evidence_count == 3
    assert result.dashboard.verification_count == 3
    assert result.dashboard.archive_entry_count == 3
    assert result.analytics.trends.points[0].session_id == result.sessions[0].session.session_id


def test_replay_integration() -> None:
    result = _build(_scenario(0), _scenario(1, replay=False))
    assert result.analytics.replay.expected_evidence_count == 2
    assert result.analytics.replay.replayed_evidence_count == 1
    assert result.analytics.replay.replay_coverage == 50
    assert result.dashboard.replay_coverage == 50


def test_cross_layer_invariant_violation_is_detected() -> None:
    result = _build(_scenario(0))
    corrupt_dashboard = result.dashboard.model_copy(update={"evidence_count": 99})
    corrupt = result.model_copy(update={"dashboard": corrupt_dashboard})
    validation = validate_cross_layer(corrupt)
    assert validation.valid is False
    assert "integration-dashboard-evidence-count-mismatch" in validation.findings

    stale_archive = result.archive_verification.model_copy(update={"archive_count": 99})
    stale = result.model_copy(update={"archive_verification": stale_archive})
    assert "archive-verification-summary-mismatch" in validate_cross_layer(stale).findings


def test_dashboard_and_analytics_refresh_are_consistent() -> None:
    result = _build(_scenario(0), _scenario(1))
    refreshed = refresh_integration_analytics(result)
    assert refreshed.analytics.canonical_json() == result.analytics.canonical_json()
    assert refreshed.dashboard.canonical_json() == result.dashboard.canonical_json()
    assert refreshed.validation.valid is True


def test_pipeline_output_is_deterministic() -> None:
    scenarios = (_scenario(0), _scenario(1), _scenario(2))
    first = _build(*scenarios)
    second = _build(*reversed(scenarios))
    assert first.canonical_json() == second.canonical_json()


def test_stress_validation_with_increasing_session_counts() -> None:
    for count in (1, 5, 20):
        result = _build(*(_scenario(index) for index in range(count)))
        assert result.validation.valid is True
        assert result.dashboard.session_count == count
        assert result.dashboard.evidence_count == count
        assert result.dashboard.archive_entry_count == count
        assert result.dashboard.replay_coverage == 100


def test_phase13_import_boundary_and_no_execution_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aios" / "observation" / "integration"
    allowed = (
        "src.aios.contracts.identifiers", "src.aios.provenance", "src.aios.observation",
    )
    forbidden = {"execute", "trade", "submit_order", "schedule", "persist", "migrate", "enforce", "sign"}
    violations: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("src."):
                if not node.module.startswith(allowed):
                    violations.append(f"{path.name}: {node.module}")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden:
                violations.append(f"{path.name}: forbidden API {node.name}")
    assert violations == []
