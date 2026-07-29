"""Audit evidence constructors for flag observations."""
from __future__ import annotations
from datetime import datetime, timezone
from src.governance.audit.events import AuditEvent
from src.flags.evaluator import FlagEvaluation


def flag_audit_event(result: FlagEvaluation, *, event_id: str = "flag-observation") -> AuditEvent:
    return AuditEvent(event_id=event_id, event_type="flag.evaluated", occurred_at=datetime.now(timezone.utc), subject_digest=result.snapshot_digest, payload=result.model_dump(mode="json"), evidence_refs=(f"flag:{result.flag}",))


def kill_audit_event(result: dict[str, object], *, subject_digest: str, event_id: str = "kill-observation") -> AuditEvent:
    return AuditEvent(event_id=event_id, event_type="kill-switch.evaluated", occurred_at=datetime.now(timezone.utc), subject_digest=subject_digest, payload=result, evidence_refs=("authority:existing-halt",))