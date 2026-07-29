"""Content-addressed orchestration observations."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"event payload is not JSON-compatible: {type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class OrchestrationEvent:
    event_id: str
    event_type: str
    observed_at: str
    plan_digest: str
    context_digest: str
    payload: Mapping[str, Any]
    previous_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _freeze(self.payload))

    def canonical_json(self) -> str:
        return json.dumps({"context_digest": self.context_digest, "event_id": self.event_id,
                           "event_type": self.event_type, "observed_at": self.observed_at,
                           "payload": _thaw(self.payload), "plan_digest": self.plan_digest,
                           "previous_digest": self.previous_digest}, sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()