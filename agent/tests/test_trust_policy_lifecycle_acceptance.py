"""Sprint 5 acceptance tests for immutable trust-policy lifecycle."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.aios.provenance.authenticity import (
    IssuerIdentity,
    RepositoryTrustedIssuerPolicy,
    TrustPolicyRepository,
    verify_authenticity,
)
from src.aios.provenance.evidence import EvidenceRecord

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def _evidence() -> EvidenceRecord:
    unsealed = EvidenceRecord.model_construct(
        evidence_id="lifecycle-evidence",
        evidence_type="runtime-observation",
        issuer_id="observer-one",
        observed_at=NOW,
        subject_digest="a" * 64,
        references=(),
        attributes={"source": "historical-observation"},
        expected_digest="",
    )
    expected = hashlib.sha256(unsealed.canonical_json().encode("utf-8")).hexdigest()
    return EvidenceRecord(**unsealed.model_dump(exclude={"expected_digest"}), expected_digest=expected)


def _snapshot(*, version: int = 1, effective_at: datetime | None = None, expires_at: datetime | None = None):
    return RepositoryTrustedIssuerPolicy(
        policy_id="repository-evidence",
        version=version,
        effective_at=effective_at or NOW - timedelta(days=1),
        expires_at=expires_at or NOW + timedelta(days=1),
        issuers=(IssuerIdentity(issuer_id="observer-one", display_name="Observer One", trust_domain="repository", trusted=True, allowed_evidence_types=("runtime-observation",)),),
    )


def test_valid_policy_snapshot_is_pinned_by_verification() -> None:
    snapshot = _snapshot(version=3)
    result = verify_authenticity(_evidence(), snapshot)
    assert result.authentic is True
    assert (result.policy_id, result.policy_version, result.policy_digest) == (snapshot.policy_id, 3, snapshot.policy_digest)
    with pytest.raises(ValidationError):
        snapshot.version = 4  # type: ignore[misc]


@pytest.mark.parametrize(
    ("effective_at", "expires_at"),
    [(NOW - timedelta(days=2), NOW), (NOW + timedelta(seconds=1), NOW + timedelta(days=2))],
    ids=("expired-policy", "future-policy"),
)
def test_inactive_policy_fails_closed(effective_at: datetime, expires_at: datetime) -> None:
    result = verify_authenticity(_evidence(), _snapshot(effective_at=effective_at, expires_at=expires_at))
    assert result.authentic is False
    assert result.reason == "trust policy snapshot is not effective at the verification time"


def test_duplicate_policy_identifier_version_is_rejected() -> None:
    snapshot = _snapshot()
    with pytest.raises(ValidationError, match="duplicate trust policy identifier/version"):
        TrustPolicyRepository(snapshots=(snapshot, snapshot))


def test_historical_policy_lookup_selects_exact_version() -> None:
    first, second = _snapshot(version=1), _snapshot(version=2)
    repository = TrustPolicyRepository(snapshots=(second, first))
    assert repository.lookup("repository-evidence", 1) is first
    assert repository.lookup("repository-evidence", 2) is second
    with pytest.raises(LookupError):
        repository.lookup("repository-evidence", 3)


def test_policy_digest_is_canonical_and_content_sensitive() -> None:
    snapshot = _snapshot()
    assert len(snapshot.policy_digest) == 64
    assert snapshot.policy_digest == _snapshot().policy_digest
    assert snapshot.policy_digest != _snapshot(version=2).policy_digest


def test_snapshot_serialization_is_deterministic() -> None:
    first, second = _snapshot(), _snapshot()
    assert first.canonical_json() == second.canonical_json()
    assert '"policy_id":"repository-evidence"' in first.canonical_json()
    assert first.model_dump_json() == second.model_dump_json()


def test_naive_verification_time_is_rejected_fail_closed() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        verify_authenticity(_evidence(), _snapshot(), verified_at=datetime(2026, 7, 29))