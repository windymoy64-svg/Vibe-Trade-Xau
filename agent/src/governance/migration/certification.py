"""Content-addressed certification artifact."""
from __future__ import annotations
import hashlib
from typing import Mapping, Any
from types import MappingProxyType
from src.aios.provenance.serialization import canonical_json

def certify(readiness: Any, *, evidence_digest: str = "") -> Mapping[str, Any]:
    body = {"schema": "phase-7", "status": readiness.status, "score": readiness.score, "evidence_digest": evidence_digest, "runtime_change": False}
    body["certification_digest"] = hashlib.sha256(canonical_json(body).encode()).hexdigest()
    return MappingProxyType(body)