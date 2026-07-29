"""Zero-import, report-only observer for built-in channel module discovery."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from src.registries.bootstrap.tools import _agent_root, _record, _report
from src.registries.core.records import RegistryRecord

_INTERNAL = frozenset({"base", "bus", "config", "manager", "pairing", "registry", "runtime", "utils"})


def _names(root: Path) -> list[str]:
    return sorted(path.stem for path in (root / "src" / "channels").glob("*.py")
                  if path.stem not in _INTERNAL and not path.stem.startswith("_"))


def discover_candidates(root: Path | None = None) -> tuple[RegistryRecord, ...]:
    root = _agent_root(root)
    records = []
    for name in _names(root):
        path = root / "src" / "channels" / f"{name}.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef) and
                   any(ast.unparse(base).split(".")[-1] == "BaseChannel" for base in node.bases)]
        records.append(_record(
            "channel", name, path, root,
            {"channel_classes": classes, "discovery_mechanism": "pkgutil.iter_modules-zero-import"},
        ))
    return tuple(records)


def inventory_report(root: Path | None = None) -> dict[str, Any]:
    root = _agent_root(root)
    return _report("channel", _names(root), discover_candidates(root))


__all__ = ["discover_candidates", "inventory_report"]