"""Deterministic aggregation of phase evidence; observation only."""
from __future__ import annotations
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Any

@dataclass(frozen=True)
class EvidenceBundle:
    phases: Mapping[str, tuple[Mapping[str, Any], ...]]
    def __post_init__(self) -> None:
        object.__setattr__(self, "phases", MappingProxyType({str(k): tuple(dict(x) for x in v) for k, v in sorted(self.phases.items())}))

def aggregate_evidence(records: Mapping[str, Any]) -> EvidenceBundle:
    return EvidenceBundle({str(k): tuple(v) if isinstance(v, (list, tuple)) else (v,) for k, v in records.items()})

def flatten(bundle: EvidenceBundle) -> tuple[Mapping[str, Any], ...]:
    return tuple(item for phase in sorted(bundle.phases) for item in bundle.phases[phase])