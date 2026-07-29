"""Report-only bootstrap catalog for the legacy LLM provider JSON artifact."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.registries.bootstrap.tools import _agent_root, _record, _report
from src.registries.core.records import RegistryRecord


def discover_candidates(root: Path | None = None) -> tuple[RegistryRecord, ...]:
    root = _agent_root(root)
    path = root / "src" / "providers" / "llm_providers.json"
    providers: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return tuple(_record(
        "provider", item["name"], path, root,
        {"provider": item, "discovery_mechanism": "llm-provider-json"},
    ) for item in sorted(providers, key=lambda value: value["name"]))


def inventory_report(root: Path | None = None) -> dict[str, Any]:
    root = _agent_root(root)
    path = root / "src" / "providers" / "llm_providers.json"
    expected = [item["name"] for item in json.loads(path.read_text(encoding="utf-8"))]
    return _report("provider", expected, discover_candidates(root))


__all__ = ["discover_candidates", "inventory_report"]