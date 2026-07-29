"""Atomic JSON-file implementation of the generic registry store."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.aios.contracts.identifiers import ResourceId
from src.registries.core.errors import CorruptRegistryError, DuplicateRecordError
from src.registries.core.records import RegistryKey, RegistryRecord

_STORE_SCHEMA_VERSION = 1


class FileRegistryStore:
    """Single-file local registry with strict validation and atomic replacement."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    def publish(self, record: RegistryRecord) -> RegistryRecord:
        sealed = record if record.digest is not None else record.sealed()
        with self._lock:
            records = list(self._load())
            if any(item.key == sealed.key for item in records):
                raise DuplicateRecordError(f"registry record already exists: {sealed.key}")
            records.append(sealed)
            records.sort(key=lambda item: item.key.canonical)
            self._save(tuple(records))
        return sealed

    def get(self, key: RegistryKey) -> RegistryRecord | None:
        with self._lock:
            return next((item for item in self._load() if item.key == key), None)

    def list(self, *, resource: ResourceId | None = None) -> tuple[RegistryRecord, ...]:
        with self._lock:
            records = self._load()
        if resource is not None:
            records = tuple(item for item in records if item.key.resource == resource)
        return records

    def _load(self) -> tuple[RegistryRecord, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            raw_records = self._extract_records(payload)
            records = tuple(RegistryRecord.model_validate(item) for item in raw_records)
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise CorruptRegistryError(str(self.path), str(exc)) from exc
        canonical_keys = [item.key.canonical for item in records]
        if canonical_keys != sorted(canonical_keys) or len(canonical_keys) != len(set(canonical_keys)):
            raise CorruptRegistryError(str(self.path), "records are unsorted or contain duplicate keys")
        return records

    @staticmethod
    def _extract_records(payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            raise ValueError("store root must be an object")
        if payload.get("schema_version") != _STORE_SCHEMA_VERSION:
            raise ValueError("unsupported store schema_version")
        records = payload.get("records")
        if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
            raise ValueError("records must be a list of objects")
        return records

    def _save(self, records: tuple[RegistryRecord, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "schema_version": _STORE_SCHEMA_VERSION,
                "records": [item.model_dump(mode="json") for item in records],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        temp = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, payload.encode("utf-8"))
            os.fsync(fd)
            os.close(fd)
            fd = -1
            os.replace(temp, self.path)
            self._fsync_directory(self.path.parent)
        finally:
            if fd >= 0:
                os.close(fd)
            try:
                temp.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        try:
            fd = os.open(directory, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(fd)
        except OSError:
            pass
        finally:
            os.close(fd)
