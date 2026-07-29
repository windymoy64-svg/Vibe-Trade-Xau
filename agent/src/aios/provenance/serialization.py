"""Strict canonical JSON conversion for immutable evidence artifacts."""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel


def canonicalize(value: Any) -> Any:
    """Return JSON-compatible content without semantic string fallbacks.

    Mapping keys must already be strings. Tuples and other immutable sequences
    represented here become JSON arrays. Unsupported values and non-finite
    floats fail closed instead of being coerced with ``str``.
    """
    if isinstance(value, BaseModel):
        return canonicalize(value.model_dump(mode="json"))
    if is_dataclass(value) and not isinstance(value, type):
        params = getattr(type(value), "__dataclass_params__", None)
        if params is None or not params.frozen:
            raise TypeError("canonical evidence dataclasses must be frozen")
        return canonicalize({field.name: getattr(value, field.name) for field in fields(value)})
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON mapping keys must be strings")
            result[key] = canonicalize(item)
        return result
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    if isinstance(value, Enum):
        return canonicalize(value.value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON does not support non-finite floats")
        return value
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize logical content to deterministic, strict canonical JSON."""
    return json.dumps(
        canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )