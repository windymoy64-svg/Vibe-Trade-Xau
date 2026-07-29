"""Shadow-only coordination of already captured observations."""
from __future__ import annotations
from typing import Any, Iterable, Mapping
from .parity import parity_report


def coordinate(left: Iterable[Mapping[str, Any]], right: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    rows = tuple({"match": a == b} for a, b in zip(tuple(left), tuple(right)))
    return {"mode": "shadow-only", "execution_authority": "existing-runtime", "parity": parity_report(rows)}