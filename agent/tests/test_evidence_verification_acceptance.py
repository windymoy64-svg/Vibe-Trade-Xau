"""Sprint 2 acceptance tests for evidence verification hardening."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.aios.contracts.environment import ExecutionEnvironment, ReleaseChannel
from src.aios.contracts.identifiers import CorrelationId, ResourceId
from src.aios.contracts.resources import ResourceBudget
from src.aios.contracts.runtime_manifest import ResolvedReference, RuntimeManifest
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.authenticity import IssuerIdentity, RepositoryTrustedIssuerPolicy
from src.aios.provenance.manifest import ResearchRuntimeResolutionManifest
from src.aios.runtime.health import HealthSnapshot
from src.aios.runtime.isolation import IsolationProfile
from src.governance.reporting.readiness import readiness_report

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
POLICY = RepositoryTrustedIssuerPolicy(
    policy_id="acceptance-policy",
    issuers=(IssuerIdentity(issuer_id="independent-observer", display_name="Independent Observer", trust_domain="repository", trusted=True),),
)


def _runtime() -> RuntimeManifest:
    return RuntimeManifest(
        run_id=CorrelationId(value="verification-run"),
        environment=ExecutionEnvironment.RESEARCH,
        release_channel=ReleaseChannel.RESEARCH,
        resolved_at=NOW,
        dependencies=(
            ResolvedReference(
                resource=ResourceId(kind="component", namespace="evidence", name="source"),
                version="1.0.0",
                digest="a" * 64,
            ),
        ),
        resources=ResourceBudget(timeout_seconds=30),
    )


def _seal(**overrides: object) -> EvidenceRecord:
    payload = {
        "evidence_id": "evidence-one",
        "evidence_type": "runtime-observation",
        "issuer_id": "independent-observer",
        "observed_at": NOW,
        "subject_digest": "a" * 64,
        "references": (),
        "attributes": {"count": 2, "verified_by": "independent-observer"},
    }
    payload.update(overrides)
    canonical = json.dumps(
        EvidenceRecord.model_construct(**payload, expected_digest="").model_dump(
            mode="json", exclude={"expected_digest"}
        ),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return EvidenceRecord(**payload, expected_digest=hashlib.sha256(canonical.encode()).hexdigest())


def _manifest(*evidence: EvidenceRecord) -> ResearchRuntimeResolutionManifest:
    return ResearchRuntimeResolutionManifest(
        runtime=_runtime(),
        isolation=IsolationProfile(name="research-observation"),
        health=HealthSnapshot(snapshot_id="health-one", observed_at=NOW),
        evidence=evidence,
    )


def test_valid_evidence_drives_readiness_and_provenance() -> None:
    evidence = _seal()
    readiness = readiness_report((evidence,), POLICY, policy_id=POLICY.policy_id)
    provenance = _manifest(evidence).provenance_verification()
    assert readiness.ready is True
    assert readiness.digest_verified is True
    assert provenance.verified is True
    assert provenance.verified_evidence_count == 1


def test_invalid_digest_is_rejected() -> None:
    evidence = _seal().model_copy(update={"expected_digest": "f" * 64})
    assert evidence.verify().verified is False
    assert readiness_report((evidence,), POLICY, policy_id=POLICY.policy_id).ready is False
    assert _manifest(evidence).verify_provenance() is False


def test_missing_provenance_is_rejected() -> None:
    result = _manifest().provenance_verification()
    assert result.verified is False
    assert result.reasons == ("provenance evidence is missing",)


def test_altered_evidence_is_rejected() -> None:
    sealed = _seal()
    altered = sealed.model_copy(update={"attributes": {"count": 3}})
    result = altered.verify()
    assert result.verified is False
    assert result.computed_digest != result.expected_digest


def test_duplicated_evidence_is_rejected() -> None:
    evidence = _seal()
    result = _manifest(evidence, evidence).provenance_verification()
    assert result.verified is False
    assert result.duplicate_evidence_ids == ("evidence-one",)
    assert result.duplicate_evidence_digests == (evidence.expected_digest,)
    assert readiness_report((evidence, evidence), POLICY, policy_id=POLICY.policy_id).ready is False


def test_verification_output_is_immutable_and_deterministic() -> None:
    evidence = _seal()
    first = readiness_report((evidence,), POLICY, policy_id=POLICY.policy_id)
    second = readiness_report((evidence,), POLICY, policy_id=POLICY.policy_id)
    assert first == second
    assert first.canonical_json() == second.canonical_json()
    assert evidence.verify().canonical_json() == evidence.verify().canonical_json()
    assert _manifest(evidence).provenance_verification().canonical_json() == _manifest(evidence).provenance_verification().canonical_json()
    with pytest.raises(ValidationError):
        first.ready = False  # type: ignore[misc]