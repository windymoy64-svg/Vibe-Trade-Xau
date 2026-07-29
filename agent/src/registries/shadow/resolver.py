"""Deterministic shadow resolution over explicit catalog candidates."""
from __future__ import annotations
from collections.abc import Iterable
from src.aios.contracts.identifiers import FrozenContract
from src.registries.core.records import RegistryRecord


class RuntimeSelection(FrozenContract):
    kind: str
    name: str
    version: str | None = None
    digest: str | None = None


class ShadowResolution(FrozenContract):
    runtime: RuntimeSelection
    candidate_key: str | None = None
    registry_digest: str | None = None
    provenance_digest: str | None = None
    matched: bool = False
    reason: str
    authoritative_source: str = "existing-runtime"
    evidence_only: bool = True


def resolve_shadow(runtime: RuntimeSelection, records: Iterable[RegistryRecord]) -> ShadowResolution:
    ordered = sorted(records, key=lambda item: item.key.canonical)
    matches = [item for item in ordered if item.key.resource.kind == runtime.kind and item.key.resource.name == runtime.name]
    if not matches:
        return ShadowResolution(runtime=runtime, reason="no registry candidate")
    candidate = matches[0]
    provenance = candidate.metadata.get("provenance", {})
    source_digest = provenance.get("source_sha256") if hasattr(provenance, "get") else None
    exact = (runtime.version is None or runtime.version == str(candidate.key.version)) and (runtime.digest is None or runtime.digest == candidate.digest)
    return ShadowResolution(runtime=runtime, candidate_key=candidate.key.canonical, registry_digest=candidate.digest, provenance_digest=source_digest, matched=exact, reason="candidate parity" if exact else "candidate mismatch")