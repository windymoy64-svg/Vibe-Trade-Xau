"""Shadow parity aggregation."""
from __future__ import annotations
from typing import Iterable, Mapping, Any

def aggregate_parity(observations: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    rows = tuple(observations); total = len(rows); matches = sum(bool(r.get("match", False)) for r in rows)
    return {"observations": total, "matches": matches, "mismatches": total - matches, "ratio": matches / total if total else 0.0}