"""Capability resolver interfaces with no registry or runtime connection."""
from __future__ import annotations
from collections.abc import Iterable
from typing import Protocol
from src.aios.capabilities.models import CapabilityCandidate, CapabilityRequirement, CapabilityResolution
from src.aios.capabilities.validation import validate_candidate, validate_requirement


class CapabilityResolver(Protocol):
    def resolve(self, requirement: CapabilityRequirement, candidates: Iterable[CapabilityCandidate]) -> CapabilityResolution: ...


class LocalCapabilityResolver:
    """Deterministically compares caller-supplied evidence only."""
    def resolve(self, requirement: CapabilityRequirement, candidates: Iterable[CapabilityCandidate]) -> CapabilityResolution:
        validate_requirement(requirement)
        ordered = sorted(candidates, key=lambda item: (item.resource.canonical, item.version, item.digest))
        required = dict(requirement.constraints)
        for candidate in ordered:
            validate_candidate(candidate)
            if candidate.capability == requirement.name and all(dict(candidate.attributes).get(k) == v for k, v in required.items()):
                return CapabilityResolution(requirement=requirement, candidate=candidate, satisfied=True, reason="caller-supplied candidate matched", authoritative=False)
        return CapabilityResolution(requirement=requirement, satisfied=not requirement.required, reason="no matching caller-supplied candidate", authoritative=False)