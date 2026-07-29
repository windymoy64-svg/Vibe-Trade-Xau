"""Immutable shadow-comparison evidence."""
from __future__ import annotations
import hashlib, json
from src.aios.contracts.identifiers import FrozenContract
from src.registries.shadow.resolver import ShadowResolution


class ShadowComparison(FrozenContract):
    resolutions: tuple[ShadowResolution, ...]
    matches: int
    mismatches: int
    missing: int
    authoritative_source: str = "existing-runtime"
    evidence_only: bool = True

    @property
    def digest(self) -> str:
        payload = self.model_dump(mode="json")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        return hashlib.sha256(encoded).hexdigest()


def compare_shadow(resolutions: tuple[ShadowResolution, ...]) -> ShadowComparison:
    ordered = tuple(sorted(resolutions, key=lambda item: (item.runtime.kind, item.runtime.name, item.runtime.version or "")))
    missing = sum(item.candidate_key is None for item in ordered)
    matches = sum(item.matched for item in ordered)
    return ShadowComparison(resolutions=ordered, matches=matches, mismatches=len(ordered) - matches - missing, missing=missing)