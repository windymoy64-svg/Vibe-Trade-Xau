"""Audit sink protocol."""
from __future__ import annotations
from typing import Protocol
from src.governance.audit.events import AuditEvent


class AuditSink(Protocol):
    def append(self, event: AuditEvent) -> None: ...