"""Canonical readiness report serialization."""
from __future__ import annotations
from typing import Any
from src.aios.provenance.serialization import canonical_json

def render_report(readiness: Any, certification: Any) -> str:
    return canonical_json({"readiness": readiness, "certification": certification})