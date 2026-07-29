"""Immutable context attached to externally observed execution evidence."""
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
    raise TypeError(f"context value is not JSON-compatible: {type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class ExecutionContext:
    context_id: str
    observed_at: str
    authority: str
    attributes: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _freeze(self.attributes))

    def canonical_json(self) -> str:
        return json.dumps({"attributes": _thaw(self.attributes), "authority": self.authority,
                           "context_id": self.context_id, "observed_at": self.observed_at},
                          sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()