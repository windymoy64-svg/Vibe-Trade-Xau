"""Evidence-only governance readiness derived from verified evidence."""
from __future__ import annotations
from typing import Iterable
from src.aios.contracts.identifiers import FrozenContract
from src.aios.provenance.authenticity import AuthenticityVerification, TrustedIssuerPolicy, verify_authenticity
from src.aios.provenance.evidence import EvidenceRecord, EvidenceVerification
from src.aios.provenance.serialization import canonical_json


class ReadinessVerification(FrozenContract):
    """Immutable readiness observation with no runtime authority."""

    ready: bool
    evidence_count: int
    verified_evidence_count: int
    digest_verified: bool
    authenticity_verified: bool
    evidence: tuple[EvidenceVerification, ...]
    authenticity: tuple[AuthenticityVerification, ...]
    authoritative: bool = False
    evidence_only: bool = True

    def canonical_json(self) -> str:
        return canonical_json(self)


def readiness_report(
    evidence: Iterable[EvidenceRecord],
    trust_policy: TrustedIssuerPolicy,
    *,
    policy_id: str,
) -> ReadinessVerification:
    """Derive readiness from independently verified integrity and authenticity."""
    items = tuple(evidence)
    results = tuple(item.verify() for item in items)
    authenticity = tuple(verify_authenticity(item, trust_policy, policy_id=policy_id) for item in items)
    digest_verified = bool(results) and all(result.verified for result in results)
    authenticity_verified = bool(authenticity) and all(result.authentic for result in authenticity)
    unique = len({item.evidence_id for item in items}) == len(items) and len({item.expected_digest for item in items}) == len(items)
    ready = digest_verified and authenticity_verified and unique
    return ReadinessVerification(
        ready=ready,
        evidence_count=len(items),
        verified_evidence_count=sum(result.verified for result in results),
        digest_verified=digest_verified,
        authenticity_verified=authenticity_verified,
        evidence=results,
        authenticity=authenticity,
    )