"""Immutable, deterministic snapshots of externally supplied runtime observations."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping
from src.aios.provenance.serialization import canonical_json


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"observation is not JSON-compatible: {type(value).__name__}")


@dataclass(frozen=True)
class RuntimeSnapshot:
    snapshot_id: str
    observed_at: str
    authority: str
    payload: Mapping[str, Any]
    previous_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _freeze(self.payload))

    def canonical_json(self) -> str:
        return canonical_json({"authority": self.authority, "observed_at": self.observed_at,
                               "payload": self.payload, "previous_digest": self.previous_digest,
                               "snapshot_id": self.snapshot_id})

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()