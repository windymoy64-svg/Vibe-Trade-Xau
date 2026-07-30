"""Strict JSON/YAML runtime configuration loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from .runtime_config import RuntimeConfig


def load_runtime_config(source: str | Path | Mapping[str, Any] | None = None) -> RuntimeConfig:
    if source is None:
        return RuntimeConfig()
    if isinstance(source, Mapping):
        return RuntimeConfig.model_validate(dict(source))
    path = Path(source)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
    elif path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        raise ValueError("runtime config must be JSON or YAML")
    if not isinstance(payload, Mapping):
        raise ValueError("runtime config document must contain an object")
    return RuntimeConfig.model_validate(dict(payload))
