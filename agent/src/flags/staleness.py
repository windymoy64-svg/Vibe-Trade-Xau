"""Snapshot age checks."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from src.flags.snapshot import FlagSnapshot


def snapshot_age(snapshot: FlagSnapshot, *, now: datetime | None = None) -> timedelta:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return current - snapshot.utc_captured_at


def is_stale(snapshot: FlagSnapshot, *, max_age: timedelta, now: datetime | None = None) -> bool:
    return snapshot_age(snapshot, now=now) > max_age or snapshot_age(snapshot, now=now).total_seconds() < 0