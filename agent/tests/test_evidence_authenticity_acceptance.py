"""Sprint 4 acceptance tests for evidence issuer authenticity and trust."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from src.aios.provenance.authenticity import (
    IssuerIdentity,
    RepositoryTrustedIssuerPolicy,
    verify_authenticity,
)
from src.aios.provenance.evidence import EvidenceRecord

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def _identity(issuer_id: str = "observer-one", *, trusted: bool = True) -> IssuerIdentity:
    return IssuerIdentity(
        issuer_id=issuer_id,
        display_name=issuer_id.replace("-", " ").title(),
        trust_domain="repository",
        trusted=trusted,
        allowed_evidence_types=("runtime-observation",),
    )


def _policy(*identities: IssuerIdentity) -> RepositoryTrustedIssuerPolicy:
    return RepositoryTrustedIssuerPolicy(policy_id="repository-evidence-v1", issuers=identities)


def _evidence(issuer_id: str = "observer-one") -> EvidenceRecord:
    unsealed = EvidenceRecord.model_construct(
        evidence_id="authenticity-one",
        evidence_type="runtime-observation",
        issuer_id=issuer_id,
        observed_at=NOW,
        subject_digest="a" * 64,
        references=(),
        attributes={"source": "captured-observation"},
        expected_digest="",
    )
    expected = hashlib.sha256(unsealed.canonical_json().encode()).hexdigest()
    return EvidenceRecord(**unsealed.model_dump(exclude={"expected_digest"}), expected_digest=expected)


def test_trusted_issuer_is_authentic() -> None:
    result = verify_authenticity(_evidence(), _policy(_identity()), policy_id="repository-evidence-v1")
    assert result.integrity_verified is True
    assert result.authentic is True
    assert result.trusted_identity == _identity()


def test_untrusted_issuer_fails_closed() -> None:
    result = verify_authenticity(_evidence(), _policy(_identity(trusted=False)), policy_id="repository-evidence-v1")
    assert result.authentic is False
    assert result.reason == "issuer is not trusted"


def test_unknown_issuer_fails_closed() -> None:
    result = verify_authenticity(_evidence("unknown-observer"), _policy(_identity()), policy_id="repository-evidence-v1")
    assert result.authentic is False
    assert result.resolved_identity_count == 0


def test_duplicate_issuer_identifiers_fail_closed() -> None:
    result = verify_authenticity(_evidence(), _policy(_identity(), _identity()), policy_id="repository-evidence-v1")
    assert result.authentic is False
    assert result.resolved_identity_count == 2
    assert result.reason == "issuer identifier is duplicated in the trust policy"


def test_integrity_valid_authenticity_invalid_remains_separate() -> None:
    evidence = _evidence()
    result = verify_authenticity(evidence, _policy(_identity(trusted=False)), policy_id="repository-evidence-v1")
    assert evidence.verify().verified is True
    assert result.integrity_verified is True
    assert result.authentic is False


def test_authenticity_verification_is_deterministic_and_immutable() -> None:
    policy = _policy(_identity())
    first = verify_authenticity(_evidence(), policy, policy_id=policy.policy_id)
    second = verify_authenticity(_evidence(), policy, policy_id=policy.policy_id)
    assert first == second
    assert first.canonical_json() == second.canonical_json()
    assert first.model_config.get("frozen") is True