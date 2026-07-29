"""Configurable, non-enforcing governance gates."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping

class GateStatus(str, Enum): PASS="PASS"; WARN="WARN"; FAIL="FAIL"
@dataclass(frozen=True)
class GateResult:
    name: str; status: GateStatus; score: int; rationale: str

def evaluate_gates(scores: Mapping[str, int], *, minimum: int = 80, warning: int = 60) -> tuple[GateResult, ...]:
    return tuple(GateResult(k, GateStatus.PASS if v >= minimum else GateStatus.WARN if v >= warning else GateStatus.FAIL, int(v), "evidence-only evaluation") for k, v in sorted(scores.items()))