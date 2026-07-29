"""Read-only adapter serialization; it never calls or mutates a runtime."""
from __future__ import annotations
from typing import Any, Mapping
from .runtime_snapshot import RuntimeSnapshot


def snapshot_from_observation(observation: Mapping[str, Any], *, snapshot_id: str,
                              observed_at: str, authority: str = "existing-runtime",
                              previous_digest: str = "") -> RuntimeSnapshot:
    return RuntimeSnapshot(snapshot_id, observed_at, authority, dict(observation), previous_digest)


def serialize_snapshot(snapshot: RuntimeSnapshot) -> str:
    return snapshot.canonical_json()