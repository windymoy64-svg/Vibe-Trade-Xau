"""Deterministic parity calculations over immutable comparison rows."""
from __future__ import annotations
from typing import Any, Iterable, Mapping


def parity_report(rows: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    values = tuple(rows)
    matches = sum(bool(row.get("match", False)) for row in values)
    return {"count": len(values), "matches": matches, "mismatches": len(values) - matches,
            "ratio": matches / len(values) if values else 0.0}