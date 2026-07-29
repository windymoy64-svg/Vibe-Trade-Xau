"""Thread-safe in-memory reference implementation of RegistryStore."""

from __future__ import annotations

import threading

from src.aios.contracts.identifiers import ResourceId
from src.registries.core.errors import DuplicateRecordError
from src.registries.core.records import RegistryKey, RegistryRecord


class MemoryRegistryStore:
    """Process-local immutable registry suitable for tests and local composition."""

    def __init__(self) -> None:
        self._records: dict[str, RegistryRecord] = {}
        self._lock = threading.RLock()

    def publish(self, record: RegistryRecord) -> RegistryRecord:
        sealed = record if record.digest is not None else record.sealed()
        key = sealed.key.canonical
        with self._lock:
            if key in self._records:
                raise DuplicateRecordError(f"registry record already exists: {key}")
            self._records[key] = sealed
        return sealed

    def get(self, key: RegistryKey) -> RegistryRecord | None:
        with self._lock:
            return self._records.get(key.canonical)

    def list(self, *, resource: ResourceId | None = None) -> tuple[RegistryRecord, ...]:
        with self._lock:
            records = tuple(self._records.values())
        if resource is not None:
            records = tuple(item for item in records if item.key.resource == resource)
        return tuple(sorted(records, key=lambda item: item.key.canonical))
