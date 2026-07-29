"""Report-only bootstrap catalog for bundled and user swarm preset artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.registries.bootstrap.tools import _agent_root, _record, _report
from src.registries.core.records import RegistryRecord


def _preset_paths(root: Path, user_presets_dir: Path | None) -> dict[str, Path]:
    bundled = root / "src" / "swarm" / "presets"
    paths = {path.stem: path for path in sorted(bundled.glob("*.yaml"))}
    if user_presets_dir is not None and user_presets_dir.is_dir():
        paths.update({path.stem: path for path in sorted(user_presets_dir.glob("*.yaml"))})
    return paths


def discover_candidates(
    root: Path | None = None, *, user_presets_dir: Path | None = None
) -> tuple[RegistryRecord, ...]:
    """Read preset YAML; user artifacts are opt-in to avoid reading ambient state."""
    root = _agent_root(root)
    records = []
    for stem, path in sorted(_preset_paths(root, user_presets_dir).items()):
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        records.append(_record(
            "swarm", stem, path, root if path.is_relative_to(root) else path.parent,
            {"declared_name": data.get("name", stem), "title": data.get("title", ""),
             "agent_count": len(data.get("agents", [])), "task_count": len(data.get("tasks", [])),
             "discovery_mechanism": "preset-search-path-user-first"},
        ))
    return tuple(records)


def inventory_report(root: Path | None = None, *, user_presets_dir: Path | None = None) -> dict[str, Any]:
    root = _agent_root(root)
    expected = _preset_paths(root, user_presets_dir)
    return _report("swarm", expected, discover_candidates(root, user_presets_dir=user_presets_dir))


__all__ = ["discover_candidates", "inventory_report"]