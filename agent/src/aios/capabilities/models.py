"""Immutable capability request and candidate contracts."""
from __future__ import annotations
from src.aios.contracts.identifiers import FrozenContract, ResourceId


class CapabilityRequirement(FrozenContract):
    name: str
    required: bool = True
    constraints: tuple[tuple[str, str], ...] = ()


class CapabilityCandidate(FrozenContract):
    capability: str
    resource: ResourceId
    version: str
    digest: str
    attributes: tuple[tuple[str, str], ...] = ()


class CapabilityResolution(FrozenContract):
    requirement: CapabilityRequirement
    candidate: CapabilityCandidate | None = None
    satisfied: bool = False
    reason: str
    authoritative: bool = False