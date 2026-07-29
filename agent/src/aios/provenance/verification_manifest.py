"""Immutable evidence-only manifests binding evidence, policy, and verification."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.provenance.authenticity import RepositoryTrustedIssuerPolicy, verify_authenticity
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.serialization import canonical_json

_IDENTIFIER_DOMAIN = "aios-verification-manifest-v1"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class VerificationManifest(FrozenContract):
    """Reproducible audit artifact with no runtime or execution authority."""

    schema_version: int = 1
    manifest_id: str
    evidence_id: str
    evidence_digest: str
    policy_id: str
    policy_version: int
    policy_digest: str
    integrity_verified: bool
    authentic: bool
    verification_reason: str
    verified_at: datetime
    authoritative: bool = False
    evidence_only: bool = True

    @field_validator("evidence_digest", "policy_digest")
    @classmethod
    def _digest(cls, value: str, info: object) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError(f"{getattr(info, 'field_name', 'digest')} must be a SHA-256 hex digest")
        return normalized

    @field_validator("verified_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("verified_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _consistent(self) -> "VerificationManifest":
        if self.schema_version != 1:
            raise ValueError("unsupported verification manifest schema version")
        if self.policy_version < 1:
            raise ValueError("policy version must be a positive integer")
        if not self.evidence_id or not self.policy_id or not self.verification_reason:
            raise ValueError("verification manifest is incomplete")
        if self.authoritative or not self.evidence_only:
            raise ValueError("verification manifests must remain evidence-only")
        if self.authentic and not self.integrity_verified:
            raise ValueError("authentic outcome requires verified evidence integrity")
        expected = self._compute_manifest_id(self._identity_payload())
        if not hmac.compare_digest(self.manifest_id, expected):
            raise ValueError("manifest identifier does not match canonical verification metadata")
        return self

    def _identity_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"manifest_id"})

    @staticmethod
    def _compute_manifest_id(payload: dict[str, Any]) -> str:
        return _sha256(canonical_json({"domain": _IDENTIFIER_DOMAIN, "manifest": payload}))

    @classmethod
    def create(
        cls,
        evidence: EvidenceRecord,
        policy: RepositoryTrustedIssuerPolicy,
        *,
        verified_at: datetime,
    ) -> "VerificationManifest":
        """Bind one evidence record to one explicit policy snapshot and result."""
        result = verify_authenticity(evidence, policy, verified_at=verified_at)
        payload = {
            "schema_version": 1,
            "evidence_id": evidence.evidence_id,
            "evidence_digest": evidence.expected_digest,
            "policy_id": result.policy_id,
            "policy_version": result.policy_version,
            "policy_digest": result.policy_digest,
            "integrity_verified": result.integrity_verified,
            "authentic": result.authentic,
            "verification_reason": result.reason,
            "verified_at": verified_at,
            "authoritative": False,
            "evidence_only": True,
        }
        canonical_payload = cls.model_construct(manifest_id="", **payload)._identity_payload()
        return cls(manifest_id=cls._compute_manifest_id(canonical_payload), **payload)

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return _sha256(self.canonical_json())

    def replay_matches(self, evidence: EvidenceRecord, policy: RepositoryTrustedIssuerPolicy) -> bool:
        """Reproduce verification from stored metadata without current-policy state."""
        try:
            replayed = type(self).create(evidence, policy, verified_at=self.verified_at)
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(self.digest, replayed.digest)