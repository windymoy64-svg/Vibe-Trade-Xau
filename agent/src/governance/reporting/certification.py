"""Evidence-only certification summary."""
from __future__ import annotations
from typing import Any, Iterable
from src.governance.audit.events import AuditEvent


def certification_report(events: Iterable[AuditEvent]) -> dict[str, Any]:
    items = tuple(events)
    return {"certifiable": False, "event_count": len(items), "evidence_refs": sorted({ref for e in items for ref in e.evidence_refs}), "authoritative": False, "reason": "Phase 3 observation only"}