"""Reproducible scoring of immutable evidence."""
from __future__ import annotations
from typing import Mapping, Any

def score_evidence(evidence: Mapping[str, Any]) -> int:
    """Return a bounded integer score; explicit boolean evidence is weighted equally."""
    if not evidence: return 0
    values = [1 if v is True or (isinstance(v, (int, float)) and v >= 1) else 0 for v in evidence.values()]
    return round(100 * sum(values) / len(values))

def summarize_scores(scores: Mapping[str, int]) -> Mapping[str, Any]:
    ordered = {str(k): int(scores[k]) for k in sorted(scores)}
    return {"scores": ordered, "total": sum(ordered.values()), "count": len(ordered), "average": round(sum(ordered.values()) / len(ordered), 4) if ordered else 0.0}