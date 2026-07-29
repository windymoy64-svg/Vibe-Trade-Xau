"""Static, report-only observer for built-in trading connector profiles."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from src.registries.bootstrap.tools import _agent_root, _literal, _record, _report
from src.registries.core.records import RegistryRecord


def _profiles(root: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    found = []
    for path in sorted((root / "src" / "trading" / "connectors").glob("*/profiles.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or ast.unparse(node.func).split(".")[-1] != "TradingProfile":
                continue
            values = {kw.arg: _literal(kw.value) for kw in node.keywords if kw.arg}
            if isinstance(values.get("id"), str):
                found.append((values["id"], path, values))
    return found


def discover_candidates(root: Path | None = None) -> tuple[RegistryRecord, ...]:
    root = _agent_root(root)
    return tuple(_record(
        "connector", profile_id, path, root,
        {"profile": values, "discovery_mechanism": "BUILTIN_PROFILES-static-expansion"},
    ) for profile_id, path, values in sorted(_profiles(root)))


def inventory_report(root: Path | None = None) -> dict[str, Any]:
    root = _agent_root(root)
    expected = [item[0] for item in _profiles(root)]
    return _report("connector", expected, discover_candidates(root))


__all__ = ["discover_candidates", "inventory_report"]