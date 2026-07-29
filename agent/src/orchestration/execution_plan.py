"""Immutable description of an observed plan; never an executable command."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    step_refs: tuple[str, ...]
    source_digest: str
    schema_version: int = 1

    def canonical_json(self) -> str:
        return json.dumps({"plan_id": self.plan_id, "schema_version": self.schema_version,
                           "source_digest": self.source_digest, "step_refs": self.step_refs},
                          sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()