"""Deterministic report envelope for shadow comparison evidence."""
from __future__ import annotations
from pydantic import model_validator
from src.aios.contracts.identifiers import FrozenContract
from src.registries.shadow.comparison import ShadowComparison


class ShadowReport(FrozenContract):
    comparison: ShadowComparison
    comparison_digest: str
    registry_digests: tuple[str, ...]
    provenance_digests: tuple[str, ...]
    authoritative: bool = False
    evidence_only: bool = True

    @model_validator(mode="after")
    def _shadow_only(self) -> "ShadowReport":
        if self.authoritative or not self.evidence_only:
            raise ValueError("shadow reports must remain non-authoritative evidence")
        return self


def build_report(comparison: ShadowComparison) -> ShadowReport:
    registry = tuple(sorted({item.registry_digest for item in comparison.resolutions if item.registry_digest}))
    provenance = tuple(sorted({item.provenance_digest for item in comparison.resolutions if item.provenance_digest}))
    return ShadowReport(comparison=comparison, comparison_digest=comparison.digest, registry_digests=registry, provenance_digests=provenance)