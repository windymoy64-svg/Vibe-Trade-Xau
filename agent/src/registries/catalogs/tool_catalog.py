"""Typed, non-authoritative catalog of bootstrap tool candidates."""
from __future__ import annotations
import hashlib, json
from collections.abc import Iterable
from pydantic import model_validator
from src.aios.contracts.identifiers import FrozenContract
from src.registries.core.records import RegistryRecord


def _validated(records: Iterable[RegistryRecord], kind: str) -> tuple[RegistryRecord, ...]:
    items = tuple(sorted(records, key=lambda item: item.key.canonical))
    for record in items:
        labels = dict(record.labels)
        if record.key.resource.kind != kind or labels.get("authority") != "candidate-only":
            raise ValueError(f"{kind} catalog accepts candidate-only {kind} records")
        if record.digest is None or record.digest != record.content_digest():
            raise ValueError("catalog records must carry verified registry digests")
        provenance = record.metadata.get("provenance")
        if not isinstance(provenance, dict) and not hasattr(provenance, "get"):
            raise ValueError("catalog records must preserve bootstrap provenance")
        if not provenance.get("source_sha256"):
            raise ValueError("catalog provenance requires source_sha256")
    if len({item.key.canonical for item in items}) != len(items):
        raise ValueError("catalog record keys must be unique")
    return items


class ToolCatalog(FrozenContract):
    records: tuple[RegistryRecord, ...]
    authoritative: bool = False

    @model_validator(mode="after")
    def _shadow_only(self) -> "ToolCatalog":
        if self.authoritative:
            raise ValueError("typed catalogs are non-authoritative")
        return self

    @classmethod
    def from_candidates(cls, records: Iterable[RegistryRecord]) -> "ToolCatalog":
        return cls(records=_validated(records, "tool"))

    @property
    def digest(self) -> str:
        values = [record.digest for record in self.records]
        return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()