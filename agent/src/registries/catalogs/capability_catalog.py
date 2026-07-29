"""Typed, non-authoritative catalog of capability candidate records."""
from __future__ import annotations
from collections.abc import Iterable
from pydantic import model_validator
from src.aios.capabilities.models import CapabilityCandidate
from src.aios.capabilities.validation import validate_candidate
from src.aios.contracts.identifiers import FrozenContract


class CapabilityCatalog(FrozenContract):
    candidates: tuple[CapabilityCandidate, ...]
    authoritative: bool = False

    @model_validator(mode="after")
    def _shadow_only(self) -> "CapabilityCatalog":
        if self.authoritative:
            raise ValueError("typed catalogs are non-authoritative")
        return self

    @classmethod
    def from_candidates(cls, candidates: Iterable[CapabilityCandidate]) -> "CapabilityCatalog":
        items = tuple(sorted(candidates, key=lambda item: (item.capability, item.resource.canonical, item.version, item.digest)))
        for candidate in items:
            validate_candidate(candidate)
        if len({(item.capability, item.resource.canonical, item.version, item.digest) for item in items}) != len(items):
            raise ValueError("capability candidates must be unique")
        return cls(candidates=items)