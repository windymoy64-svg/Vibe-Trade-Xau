"""Deterministic timeline generation from immutable events."""
from __future__ import annotations
from typing import Any, Iterable, Mapping
from types import MappingProxyType
from ..orchestration_events import OrchestrationEvent


def build_timeline(events: Iterable[OrchestrationEvent]) -> tuple[Mapping[str, Any], ...]:
    ordered = sorted(events, key=lambda e: (e.observed_at, e.event_id, e.digest()))
    return tuple(MappingProxyType({"event_id": e.event_id, "event_type": e.event_type,
                  "observed_at": e.observed_at, "event_digest": e.digest(),
                  "previous_digest": e.previous_digest}) for e in ordered)