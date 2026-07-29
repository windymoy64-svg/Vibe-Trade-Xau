"""Research Runtime Resolution Manifest (RRM) and integrity helpers."""
from __future__ import annotations
import hashlib
from pydantic import model_validator
from src.aios.capabilities.models import CapabilityResolution
from src.aios.contracts.environment import ExecutionEnvironment
from src.aios.contracts.identifiers import FrozenContract
from src.aios.contracts.runtime_manifest import RuntimeManifest
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.serialization import canonical_json
from src.aios.runtime.health import HealthSnapshot
from src.aios.runtime.isolation import IsolationProfile


class ProvenanceVerification(FrozenContract):
    """Immutable aggregate verification result; it carries no authority."""

    verified: bool
    evidence_count: int
    verified_evidence_count: int
    duplicate_evidence_ids: tuple[str, ...] = ()
    duplicate_evidence_digests: tuple[str, ...] = ()
    missing_references: tuple[str, ...] = ()
    unanchored_evidence_ids: tuple[str, ...] = ()
    invalid_evidence_ids: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    authoritative: bool = False

    def canonical_json(self) -> str:
        return canonical_json(self)


class ResearchRuntimeResolutionManifest(FrozenContract):
    schema_version: int = 1
    runtime: RuntimeManifest
    capabilities: tuple[CapabilityResolution, ...] = ()
    isolation: IsolationProfile
    health: HealthSnapshot
    evidence: tuple[EvidenceRecord, ...] = ()
    authoritative: bool = False

    @model_validator(mode="after")
    def _research_only(self) -> "ResearchRuntimeResolutionManifest":
        if self.runtime.environment != ExecutionEnvironment.RESEARCH:
            raise ValueError("RRM is research-only")
        if self.authoritative:
            raise ValueError("Phase 5 RRM cannot be authoritative")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def runtime_digest(self) -> str:
        payload = canonical_json(self.runtime)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def provenance_verification(self) -> ProvenanceVerification:
        """Verify seals, uniqueness, references, and provenance anchors."""
        items = self.evidence
        if not items:
            return ProvenanceVerification(
                verified=False,
                evidence_count=0,
                verified_evidence_count=0,
                reasons=("provenance evidence is missing",),
            )

        ids = tuple(item.evidence_id for item in items)
        digests = tuple(item.expected_digest for item in items)
        duplicate_ids = tuple(sorted({value for value in ids if ids.count(value) > 1}))
        duplicate_digests = tuple(sorted({value for value in digests if digests.count(value) > 1}))
        known_references = frozenset(ids) | frozenset(digests)
        missing_references = tuple(sorted({ref for item in items for ref in item.references if ref not in known_references}))
        valid_subjects = {self.runtime_digest, *(dependency.digest for dependency in self.runtime.dependencies)}
        unanchored = tuple(sorted(item.evidence_id for item in items if item.subject_digest not in valid_subjects))
        results = tuple(item.verify() for item in items)
        invalid = tuple(sorted(result.evidence_id for result in results if not result.verified))

        reasons: list[str] = []
        if duplicate_ids:
            reasons.append("duplicate evidence identifiers")
        if duplicate_digests:
            reasons.append("duplicate evidence digests")
        if missing_references:
            reasons.append("evidence references are incomplete")
        if unanchored:
            reasons.append("evidence is not anchored to the runtime or a pinned dependency")
        if invalid:
            reasons.append("evidence digest verification failed")

        return ProvenanceVerification(
            verified=not reasons,
            evidence_count=len(items),
            verified_evidence_count=sum(result.verified for result in results),
            duplicate_evidence_ids=duplicate_ids,
            duplicate_evidence_digests=duplicate_digests,
            missing_references=missing_references,
            unanchored_evidence_ids=unanchored,
            invalid_evidence_ids=invalid,
            reasons=tuple(reasons),
        )

    def verify_provenance(self) -> bool:
        """Compatibility predicate backed by complete provenance verification."""
        return self.provenance_verification().verified