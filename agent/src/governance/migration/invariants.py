"""Invariant validation over supplied evidence, never runtime state."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any

NAMES = ("runtime_authority", "provenance_completeness", "digest_integrity", "shadow_parity")
@dataclass(frozen=True)
class InvariantResult:
    name: str; passed: bool; rationale: str

def validate_invariants(evidence: Mapping[str, Any]) -> tuple[InvariantResult, ...]:
    return tuple(InvariantResult(n, evidence.get(n) is True, "present and true" if evidence.get(n) is True else "missing or not affirmed") for n in NAMES)