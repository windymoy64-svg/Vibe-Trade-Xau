"""Deterministic batches of archive entries ordered by entry digest."""
from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.archive.entry import ObservationArchiveEntry
from src.aios.provenance.serialization import canonical_json

_BATCH_DOMAIN = "aios-observation-archive-batch-v1"


class ObservationArchiveBatch(FrozenContract):
    """Immutable batch of unique, deterministically ordered archive entries."""

    schema_version: int = 1
    batch_id: str
    entries: tuple[ObservationArchiveEntry, ...] = ()
    batched_at: datetime
    authoritative: bool = False
    evidence_only: bool = True

    @field_validator("batched_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("batched_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _consistent(self) -> "ObservationArchiveBatch":
        if self.schema_version != 1:
            raise ValueError("unsupported archive batch schema version")
        if self.authoritative or not self.evidence_only:
            raise ValueError("archive batches must remain evidence-only")

        entry_ids = tuple(entry.entry_id for entry in self.entries)
        if len(set(entry_ids)) != len(entry_ids):
            raise ValueError("duplicate archive entries are not permitted in a batch")
        session_ids = tuple(entry.session_id for entry in self.entries)
        if len(set(session_ids)) != len(session_ids):
            raise ValueError("duplicate observation sessions are not permitted in a batch")

        ordered = tuple(sorted(self.entries, key=lambda entry: entry.entry_id))
        if tuple(entry.entry_id for entry in ordered) != entry_ids:
            raise ValueError("archive batch entries must be ordered deterministically by entry digest")

        expected = self._compute_batch_id(self._identity_payload())
        if not hmac.compare_digest(self.batch_id, expected):
            raise ValueError("batch identifier does not match canonical batch metadata")
        return self

    def _identity_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"batch_id"})

    @staticmethod
    def _compute_batch_id(payload: dict[str, Any]) -> str:
        body = canonical_json({"domain": _BATCH_DOMAIN, "batch": payload})
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        entries: tuple[ObservationArchiveEntry, ...],
        *,
        batched_at: datetime,
    ) -> "ObservationArchiveBatch":
        """Wrap entries into a verified, canonical batch."""
        ordered = tuple(sorted(entries, key=lambda entry: entry.entry_id))
        payload = {
            "schema_version": 1,
            "entries": ordered,
            "batched_at": batched_at,
            "authoritative": False,
            "evidence_only": True,
        }
        identity = cls.model_construct(batch_id="", **payload)._identity_payload()
        return cls(batch_id=cls._compute_batch_id(identity), **payload)

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_archive_batch(
    entries: Iterable[ObservationArchiveEntry],
    *,
    batched_at: datetime,
) -> ObservationArchiveBatch:
    """Build a deterministic, duplicate-free batch from entries."""
    unique_entries: dict[str, ObservationArchiveEntry] = {}
    session_ids: set[str] = set()
    for entry in entries:
        if entry.entry_id in unique_entries:
            raise ValueError(f"duplicate archive entry detected: {entry.entry_id}")
        unique_entries[entry.entry_id] = entry
        if entry.session_id in session_ids:
            raise ValueError(f"duplicate observation session detected: {entry.session_id}")
        session_ids.add(entry.session_id)

    return ObservationArchiveBatch.create(
        entries=tuple(unique_entries.values()),
        batched_at=batched_at,
    )
