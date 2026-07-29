"""Canonical orchestration observation reports."""
from __future__ import annotations
import hashlib
import json
from typing import Any, Mapping


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


def render_report(observation: Mapping[str, Any]) -> str:
    body = {"schema": "phase-9", "observation_only": True, "observation": _thaw(observation)}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    body["report_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return json.dumps(body, sort_keys=True, separators=(",", ":"))