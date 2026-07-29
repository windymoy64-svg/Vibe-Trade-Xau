"""Fan-out audit sink; failures are surfaced, never silently converted to policy."""
from __future__ import annotations
from collections.abc import Iterable
from src.governance.audit.events import AuditEvent
from src.governance.audit.sink import AuditSink


class CompositeAuditSink:
    def __init__(self, sinks: Iterable[AuditSink] = ()) -> None:
        self.sinks = tuple(sinks)

    def append(self, event: AuditEvent) -> None:
        for sink in self.sinks:
            sink.append(event)