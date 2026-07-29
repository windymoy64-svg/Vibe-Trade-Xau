"""Bridge snapshots into content-addressed evidence records."""
from __future__ import annotations
from typing import Any, Mapping
from .runtime_snapshot import RuntimeSnapshot


def to_evidence(snapshot: RuntimeSnapshot, *, source: str = "runtime-observation") -> Mapping[str, Any]:
    return {"source": source, "snapshot_id": snapshot.snapshot_id, "snapshot_digest": snapshot.digest(),
            "previous_digest": snapshot.previous_digest, "authority": snapshot.authority,
            "observed_at": snapshot.observed_at, "payload": snapshot.payload}