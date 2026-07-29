"""Coordinate supplied orchestration evidence without execution or scheduling."""
from __future__ import annotations
from typing import Any, Iterable, Mapping
from types import MappingProxyType
from ..orchestration_events import OrchestrationEvent
from ..orchestrator import observe
from .timeline import build_timeline


def coordinate(events: Iterable[OrchestrationEvent]) -> Mapping[str, Any]:
    result = observe(tuple(events))
    return MappingProxyType({"mode": result.mode, "authority": result.authority,
                             "event_count": len(result.events),
                             "timeline": build_timeline(result.events)})