"""Shadow orchestrator accepting supplied observations only."""
from __future__ import annotations
from dataclasses import dataclass
from .observation_pipeline import build_pipeline
from .orchestration_events import OrchestrationEvent


@dataclass(frozen=True)
class ObservationResult:
    mode: str
    authority: str
    events: tuple[OrchestrationEvent, ...]


def observe(events: tuple[OrchestrationEvent, ...]) -> ObservationResult:
    return ObservationResult("observation-only", "existing-runtime", build_pipeline(events))