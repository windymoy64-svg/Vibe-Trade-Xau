"""Static, report-only observer for the backtest loader registry declarations."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from src.registries.bootstrap.tools import _agent_root, _literal, _record, _report
from src.registries.core.records import RegistryRecord


def _registered(root: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    found = []
    for path in sorted((root / "backtest" / "loaders").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not any(
                ast.unparse(dec).split(".")[-1] == "register" for dec in node.decorator_list
            ):
                continue
            values = {
                target.id: _literal(statement.value)
                for statement in node.body
                if isinstance(statement, (ast.Assign, ast.AnnAssign))
                for target in ((statement.targets[0],) if isinstance(statement, ast.Assign) else (statement.target,))
                if isinstance(target, ast.Name)
            }
            if isinstance(values.get("name"), str):
                found.append((values["name"], path, values))
    return found


def discover_candidates(root: Path | None = None) -> tuple[RegistryRecord, ...]:
    root = _agent_root(root)
    return tuple(_record(
        "loader", name, path, root,
        {"class_metadata": values, "discovery_mechanism": "@register-static-scan"},
    ) for name, path, values in sorted(_registered(root)))


def inventory_report(root: Path | None = None) -> dict[str, Any]:
    root = _agent_root(root)
    registry = root / "backtest" / "loaders" / "registry.py"
    tree = ast.parse(registry.read_text(encoding="utf-8"), filename=str(registry))
    expected: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "VALID_SOURCES":
            expected = set(ast.literal_eval(node.value)) - {"auto"}
    return _report("loader", expected, discover_candidates(root))


__all__ = ["discover_candidates", "inventory_report"]