"""Deterministic evidence pipeline accepting verified manifests only."""
from __future__ import annotations

from collections.abc import Iterable

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.provenance.serialization import canonical_json
from src.aios.provenance.verification_manifest import VerificationManifest


class EvidencePipelineEntry(FrozenContract):
    """One ordered, provenance-preserving pipeline position."""

    sequence: int
    source_id: str
    manifest: VerificationManifest
    verification_latency_ms: int = 0

    @field_validator("sequence")
    @classmethod
    def _non_negative_sequence(cls, value: int) -> int:
        if value < 0:
            raise ValueError("pipeline sequence must be non-negative")
        return value

    @field_validator("source_id")
    @classmethod
    def _source_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pipeline entry requires a source identifier")
        return value.strip().lower()

    @field_validator("verification_latency_ms")
    @classmethod
    def _non_negative_latency(cls, value: int) -> int:
        if value < 0:
            raise ValueError("verification latency must be non-negative")
        return value

    @model_validator(mode="after")
    def _verified_only(self) -> "EvidencePipelineEntry":
        if not self.manifest.integrity_verified or not self.manifest.authentic:
            raise ValueError("evidence pipeline accepts verified manifests only")
        if self.manifest.authoritative or not self.manifest.evidence_only:
            raise ValueError("pipeline entries must remain evidence-only")
        return self


class EvidencePipeline(FrozenContract):
    """Immutable ordered collection of verified verification manifests."""

    schema_version: int = 1
    entries: tuple[EvidencePipelineEntry, ...] = ()
    authoritative: bool = False
    evidence_only: bool = True

    @model_validator(mode="after")
    def _ordered_and_unique(self) -> "EvidencePipeline":
        if self.schema_version != 1:
            raise ValueError("unsupported evidence pipeline schema version")
        if self.authoritative or not self.evidence_only:
            raise ValueError("evidence pipelines must remain evidence-only")
        sequences = tuple(entry.sequence for entry in self.entries)
        if sequences != tuple(range(len(self.entries))):
            raise ValueError("pipeline sequences must be contiguous from zero")
        manifest_ids = tuple(entry.manifest.manifest_id for entry in self.entries)
        if len(set(manifest_ids)) != len(manifest_ids):
            raise ValueError("pipeline contains duplicate verification manifests")
        evidence_ids = tuple(entry.manifest.evidence_id for entry in self.entries)
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("pipeline contains duplicate evidence identifiers")
        ordered = tuple(
            sorted(
                self.entries,
                key=lambda entry: (entry.manifest.verified_at, entry.manifest.manifest_id, entry.source_id),
            )
        )
        if tuple(entry.manifest.manifest_id for entry in ordered) != manifest_ids:
            raise ValueError("pipeline entries are not deterministically ordered")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def manifest_ids(self) -> tuple[str, ...]:
        return tuple(entry.manifest.manifest_id for entry in self.entries)

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(entry.manifest.evidence_id for entry in self.entries)


def build_evidence_pipeline(
    submissions: Iterable[tuple[str, VerificationManifest, int]],
) -> EvidencePipeline:
    """Accept verified manifests only and order them deterministically."""
    prepared: list[tuple[str, VerificationManifest, int]] = []
    for source_id, manifest, latency_ms in submissions:
        if not manifest.integrity_verified or not manifest.authentic:
            raise ValueError("evidence pipeline accepts verified manifests only")
        prepared.append((source_id.strip().lower(), manifest, latency_ms))
    ordered = sorted(prepared, key=lambda item: (item[1].verified_at, item[1].manifest_id, item[0]))
    entries = tuple(
        EvidencePipelineEntry(
            sequence=index,
            source_id=source_id,
            manifest=manifest,
            verification_latency_ms=latency_ms,
        )
        for index, (source_id, manifest, latency_ms) in enumerate(ordered)
    )
    return EvidencePipeline(entries=entries)
