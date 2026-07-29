"""Canonical integration-readiness report rendering."""
from __future__ import annotations
import hashlib
from typing import Any, Mapping
from src.aios.provenance.serialization import canonical_json


def render_report(data: Mapping[str, Any]) -> str:
    body = {"schema": "phase-8", "evidence_only": True, "report": data}
    body["report_digest"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
    return canonical_json(body)