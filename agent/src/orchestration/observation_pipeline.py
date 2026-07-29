"""Pure observation pipeline that validates evidence chains without actions."""
from __future__ import annotations
from typing import Iterable
from .orchestration_events import OrchestrationEvent


def build_pipeline(events: Iterable[OrchestrationEvent]) -> tuple[OrchestrationEvent, ...]:
    items = tuple(events)
    for index, event in enumerate(items):
        if index and event.previous_digest != items[index - 1].digest():
            raise ValueError("orchestration evidence digest chain is broken")
    return items