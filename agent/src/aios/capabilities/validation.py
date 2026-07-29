"""Pure capability-contract validation."""
from __future__ import annotations
from src.aios.capabilities.models import CapabilityCandidate, CapabilityRequirement


def validate_requirement(requirement: CapabilityRequirement) -> None:
    if not requirement.name.strip():
        raise ValueError("capability name cannot be empty")
    if tuple(sorted(requirement.constraints)) != requirement.constraints:
        raise ValueError("capability constraints must be sorted")


def validate_candidate(candidate: CapabilityCandidate) -> None:
    if candidate.capability.strip() == "":
        raise ValueError("candidate capability cannot be empty")
    if len(candidate.digest) != 64 or any(char not in "0123456789abcdef" for char in candidate.digest):
        raise ValueError("candidate digest must be lowercase SHA-256")
    if tuple(sorted(candidate.attributes)) != candidate.attributes:
        raise ValueError("candidate attributes must be sorted")