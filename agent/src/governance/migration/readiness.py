"""Migration readiness evaluation as a frozen evidence artifact."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any
from .invariants import validate_invariants

@dataclass(frozen=True)
class Readiness:
    status: str; score: int; invariants: tuple[Any, ...]; recommendation: str

def evaluate_readiness(evidence: Mapping[str, Any]) -> Readiness:
    checks = validate_invariants(evidence); score = round(100 * sum(c.passed for c in checks) / len(checks))
    return Readiness("READY" if score == 100 else "NOT_READY", score, checks, "continue evidence collection" if score < 100 else "remain evidence-only")