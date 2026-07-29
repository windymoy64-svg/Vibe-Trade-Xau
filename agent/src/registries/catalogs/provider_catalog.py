"""Typed, non-authoritative catalog of bootstrap provider candidates."""
from __future__ import annotations
from collections.abc import Iterable
from pydantic import model_validator
from src.aios.contracts.identifiers import FrozenContract
from src.registries.catalogs.tool_catalog import _validated
from src.registries.core.records import RegistryRecord


class ProviderCatalog(FrozenContract):
    records: tuple[RegistryRecord, ...]
    authoritative: bool = False

    @model_validator(mode="after")
    def _shadow_only(self) -> "ProviderCatalog":
        if self.authoritative:
            raise ValueError("typed catalogs are non-authoritative")
        return self

    @classmethod
    def from_candidates(cls, records: Iterable[RegistryRecord]) -> "ProviderCatalog":
        return cls(records=_validated(records, "provider"))