"""Read-only bootstrap inventory for the legacy local-tool discovery surface.

This module deliberately parses source instead of importing ``src.tools``:
imports trigger subclass registration and availability checks.  The resulting
records are candidates only; this module never publishes to a registry store.
"""

from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.aios.contracts.compatibility import CompatibilitySpec
from src.aios.contracts.environment import ExecutionEnvironment
from src.aios.contracts.identifiers import ResourceId
from src.aios.contracts.ownership import Ownership
from src.registries.core.records import RegistryKey, RegistryRecord
from src.registries.core.versions import SemanticVersion

_OBSERVED_AT = datetime(1970, 1, 1, tzinfo=timezone.utc)
_ACTOR = ResourceId(kind="actor", namespace="bootstrap", name="phase-2-observer")
_OWNER = Ownership(technical_owner="platform-team", business_owner="product-team")


def _agent_root(root: Path | None = None) -> Path:
    return (root or Path(__file__).resolve().parents[3]).resolve()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _literal(node: ast.AST | None, default: Any = None) -> Any:
    if node is None:
        return default
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return ast.unparse(node)


def _record(kind: str, name: str, source: Path, root: Path, metadata: dict[str, Any]) -> RegistryRecord:
    provenance = {
        "discovery_mode": "static-read-only",
        "source_path": source.relative_to(root).as_posix(),
        "source_sha256": _sha256(source),
        "source_of_truth": True,
    }
    return RegistryRecord(
        key=RegistryKey(
            resource=ResourceId(kind=kind, namespace="legacy-runtime", name=name),
            version=SemanticVersion("0.0.0"),
        ),
        ownership=_OWNER,
        compatibility=CompatibilitySpec(
            api_version="0.0.0", supported_environments=(ExecutionEnvironment.RESEARCH,)
        ),
        created_at=_OBSERVED_AT,
        created_by=_ACTOR,
        labels=(("authority", "candidate-only"), ("phase", "bootstrap-2")),
        metadata={**metadata, "provenance": provenance},
    ).sealed()


def _report(kind: str, expected: Iterable[str], records: Iterable[RegistryRecord]) -> dict[str, Any]:
    expected_ids = sorted(set(expected))
    records = tuple(records)
    observed_ids = sorted(record.key.resource.name for record in records)
    missing = sorted(set(expected_ids) - set(observed_ids))
    unexpected = sorted(set(observed_ids) - set(expected_ids))
    return {
        "kind": kind,
        "authoritative": False,
        "expected_count": len(expected_ids),
        "observed_count": len(observed_ids),
        "missing": missing,
        "unexpected": unexpected,
        "parity": not missing and not unexpected and len(observed_ids) == len(set(observed_ids)),
        "inventory_digest": hashlib.sha256(
            json.dumps(observed_ids, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "record_digests_verified": all(record.digest == record.content_digest() for record in records),
    }


def discover_candidates(root: Path | None = None) -> tuple[RegistryRecord, ...]:
    """Observe named ``BaseTool`` subclasses without importing tool modules."""
    root = _agent_root(root)
    tools_dir = root / "src" / "tools"
    found: dict[str, RegistryRecord] = {}
    for path in sorted(tools_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {ast.unparse(base).split(".")[-1] for base in node.bases}
            if not ({"BaseTool", "AsyncBaseTool"} & bases):
                continue
            assignments = {
                target.id: _literal(statement.value)
                for statement in node.body
                if isinstance(statement, (ast.Assign, ast.AnnAssign))
                for target in ((statement.targets[0],) if isinstance(statement, ast.Assign) else (statement.target,))
                if isinstance(target, ast.Name)
            }
            name = assignments.get("name")
            if not isinstance(name, str) or not name:
                continue
            found[name] = _record(
                "tool", name, path, root,
                {"class_name": node.name, "description": assignments.get("description", ""),
                 "discovery_mechanism": "BaseTool.__subclasses__"},
            )
    return tuple(found[name] for name in sorted(found))


def inventory_report(root: Path | None = None) -> dict[str, Any]:
    records = discover_candidates(root)
    return _report("tool", (r.key.resource.name for r in records), records)


__all__ = ["discover_candidates", "inventory_report"]