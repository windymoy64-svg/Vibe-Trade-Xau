"""Immutable, historically reproducible repository trust-policy contracts."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract, validate_identifier_segment
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.serialization import canonical_json


class IssuerIdentity(FrozenContract):
    """Immutable repository policy metadata for one evidence issuer."""

    issuer_id: str
    display_name: str
    trust_domain: str
    trusted: bool = False
    allowed_evidence_types: tuple[str, ...] = ()

    @field_validator("issuer_id", "trust_domain", mode="before")
    @classmethod
    def _identifier(cls, value: str, info: object) -> str:
        field_name = getattr(info, "field_name", "identifier")
        return validate_identifier_segment(value, field_name=field_name)

    @field_validator("allowed_evidence_types")
    @classmethod
    def _ordered_types(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip().lower() for item in value)
        if len(set(normalized)) != len(normalized):
            raise ValueError("allowed evidence types must be unique")
        return tuple(sorted(normalized))


@runtime_checkable
class TrustedIssuerPolicy(Protocol):
    """Read-only snapshot interface; no implicit current-policy resolution."""

    policy_id: str
    version: int
    effective_at: datetime
    expires_at: datetime

    @property
    def policy_digest(self) -> str: ...

    def identities_for(self, issuer_id: str) -> tuple[IssuerIdentity, ...]: ...


class RepositoryTrustedIssuerPolicy(FrozenContract):
    """One immutable, content-addressed version of repository trust policy."""

    policy_id: str
    version: int = 1
    effective_at: datetime = datetime(1970, 1, 1, tzinfo=timezone.utc)
    expires_at: datetime = datetime.max.replace(tzinfo=timezone.utc)
    issuers: tuple[IssuerIdentity, ...] = ()

    @field_validator("policy_id", mode="before")
    @classmethod
    def _policy_identifier(cls, value: str) -> str:
        return validate_identifier_segment(value, field_name="policy_id")

    @field_validator("effective_at", "expires_at")
    @classmethod
    def _utc_interval(cls, value: datetime, info: object) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{getattr(info, 'field_name', 'policy timestamp')} must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _valid_lifecycle(self) -> "RepositoryTrustedIssuerPolicy":
        if self.version < 1:
            raise ValueError("policy version must be a positive integer")
        if self.expires_at <= self.effective_at:
            raise ValueError("policy expiry must be later than its effective time")
        return self

    def identities_for(self, issuer_id: str) -> tuple[IssuerIdentity, ...]:
        normalized = validate_identifier_segment(issuer_id, field_name="issuer_id")
        return tuple(identity for identity in self.issuers if identity.issuer_id == normalized)

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def policy_digest(self) -> str:
        """SHA-256 over all canonical snapshot metadata and policy content."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def is_effective_at(self, instant: datetime) -> bool:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("policy verification time must be timezone-aware")
        checked = instant.astimezone(timezone.utc)
        return self.effective_at <= checked < self.expires_at


class TrustPolicyRepository(FrozenContract):
    """Immutable collection supporting exact historical snapshot lookup."""

    snapshots: tuple[RepositoryTrustedIssuerPolicy, ...] = ()

    @model_validator(mode="after")
    def _unique_snapshot_keys(self) -> "TrustPolicyRepository":
        keys = tuple((item.policy_id, item.version) for item in self.snapshots)
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate trust policy identifier/version")
        return self

    def lookup(self, policy_id: str, version: int) -> RepositoryTrustedIssuerPolicy:
        normalized = validate_identifier_segment(policy_id, field_name="policy_id")
        matches = tuple(item for item in self.snapshots if item.policy_id == normalized and item.version == version)
        if len(matches) != 1:
            raise LookupError(f"trust policy snapshot not found: {normalized}@{version}")
        return matches[0]


class AuthenticityVerification(FrozenContract):
    """Immutable authenticity result, separate from evidence integrity."""

    evidence_id: str
    issuer_id: str
    policy_id: str
    policy_version: int
    policy_digest: str
    integrity_verified: bool
    authentic: bool
    resolved_identity_count: int
    trusted_identity: IssuerIdentity | None = None
    reason: str
    authoritative: bool = False

    def canonical_json(self) -> str:
        return canonical_json(self)


def verify_authenticity(
    evidence: EvidenceRecord,
    policy: TrustedIssuerPolicy,
    *,
    policy_id: str | None = None,
    verified_at: datetime | None = None,
) -> AuthenticityVerification:
    """Verify against one explicit snapshot at an explicit historical instant."""
    integrity = evidence.verify()
    identities = policy.identities_for(evidence.issuer_id)
    identity = identities[0] if len(identities) == 1 else None
    checked_at = evidence.observed_at if verified_at is None else verified_at

    if policy_id is not None and policy_id != policy.policy_id:
        reason = "policy identifier does not match the supplied snapshot"
    elif not policy.is_effective_at(checked_at):
        reason = "trust policy snapshot is not effective at the verification time"
    elif not integrity.verified:
        reason = "evidence integrity verification failed"
    elif not identities:
        reason = "issuer is unknown to the trust policy"
    elif len(identities) > 1:
        reason = "issuer identifier is duplicated in the trust policy"
    elif not identity.trusted:
        reason = "issuer is not trusted"
    elif identity.allowed_evidence_types and evidence.evidence_type.lower() not in identity.allowed_evidence_types:
        reason = "issuer is not trusted for this evidence type"
    else:
        reason = "issuer identity verified by repository trust policy"

    authentic = reason == "issuer identity verified by repository trust policy"
    return AuthenticityVerification(
        evidence_id=evidence.evidence_id,
        issuer_id=evidence.issuer_id,
        policy_id=policy.policy_id,
        policy_version=policy.version,
        policy_digest=policy.policy_digest,
        integrity_verified=integrity.verified,
        authentic=authentic,
        resolved_identity_count=len(identities),
        trusted_identity=identity if authentic else None,
        reason=reason,
    )