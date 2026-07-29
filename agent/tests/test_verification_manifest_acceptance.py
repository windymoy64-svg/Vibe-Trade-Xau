"""Sprint 6 acceptance tests for verification manifest audit traceability."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.aios.provenance.authenticity import IssuerIdentity, RepositoryTrustedIssuerPolicy
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.verification_manifest import VerificationManifest

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def _evidence() -> EvidenceRecord:
    unsealed = EvidenceRecord.model_construct(
        evidence_id="manifest-evidence",
        evidence_type="runtime-observation",
        issuer_id="audit-observer",
        observed_at=NOW,
        subject_digest="a" * 64,
        references=(),
        attributes={"scope": "verification-audit"},
        expected_digest="",
    )
    digest = hashlib.sha256(unsealed.canonical_json().encode("utf-8")).hexdigest()
    return EvidenceRecord(**unsealed.model_dump(exclude={"expected_digest"}), expected_digest=digest)


def _policy(*, version: int = 4) -> RepositoryTrustedIssuerPolicy:
    return RepositoryTrustedIssuerPolicy(
        policy_id="audit-policy",
        version=version,
        effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1),
        issuers=(IssuerIdentity(issuer_id="audit-observer", display_name="Audit Observer", trust_domain="repository", trusted=True),),
    )


def _manifest() -> VerificationManifest:
    return VerificationManifest.create(_evidence(), _policy(), verified_at=NOW)


def test_valid_verification_manifest_binds_audit_metadata() -> None:
    manifest = _manifest()
    assert manifest.authentic is True
    assert manifest.evidence_digest == _evidence().expected_digest
    assert (manifest.policy_id, manifest.policy_version, manifest.policy_digest) == ("audit-policy", 4, _policy().policy_digest)
    assert manifest.authoritative is False and manifest.evidence_only is True


@pytest.mark.parametrize(
    "changes",
    [
        {"policy_digest": "f" * 64},
        {"authentic": True, "integrity_verified": False},
        {"verification_reason": ""},
        {"authoritative": True},
    ],
)
def test_inconsistent_manifest_is_rejected(changes: dict[str, object]) -> None:
    payload = _manifest().model_dump()
    payload.update(changes)
    with pytest.raises(ValidationError):
        VerificationManifest(**payload)


def test_manifest_digest_is_stable_and_content_sensitive() -> None:
    first = _manifest()
    second = VerificationManifest.create(_evidence(), _policy(), verified_at=NOW)
    later = VerificationManifest.create(_evidence(), _policy(), verified_at=NOW + timedelta(seconds=1))
    assert first.digest == second.digest
    assert first.manifest_id == second.manifest_id
    assert first.digest != later.digest


def test_manifest_serialization_is_deterministic() -> None:
    first, second = _manifest(), _manifest()
    assert first.canonical_json() == second.canonical_json()
    assert first.canonical_json().startswith('{"authentic":true,')


def test_manifest_is_immutable() -> None:
    manifest = _manifest()
    with pytest.raises(ValidationError):
        manifest.authentic = False  # type: ignore[misc]


def test_historical_replay_uses_stored_manifest_metadata() -> None:
    manifest = _manifest()
    assert manifest.replay_matches(_evidence(), _policy()) is True
    assert manifest.replay_matches(_evidence(), _policy(version=5)) is False
    altered = _evidence().model_copy(update={"expected_digest": "f" * 64})
    assert manifest.replay_matches(altered, _policy()) is False