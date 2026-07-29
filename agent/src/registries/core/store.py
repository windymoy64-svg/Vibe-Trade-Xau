"""Storage-neutral registry store protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.aios.contracts.identifiers import ResourceId
from src.registries.core.records import RegistryKey, RegistryRecord


@runtime_checkable
class RegistryStore(Protocol):
    """Minimal immutable publication and query interface."""

    def publish(self, record: RegistryRecord) -> RegistryRecord:
        """Publish one new exact key or raise DuplicateRecordError."""
        ...

    def get(self, key: RegistryKey) -> RegistryRecord | None:
        """Retrieve one exact key."""
        ...

    def list(self, *, resource: ResourceId | None = None) -> tuple[RegistryRecord, ...]:
        """Return records in deterministic key order."""
        ...
