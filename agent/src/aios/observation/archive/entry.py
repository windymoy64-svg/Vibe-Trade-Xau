"""Immutable archive entries wrapping sealed observation sessions."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.session import ObservationSession, ObservationSessionLifecycle
from src.aios.provenance.serialization import canonical_json

_ENTRY_DOMAIN = "aios-observation-archive-entry-v1"


class ObservationArchiveEntry(FrozenContract):
    """Immutable evidence-only archive entry."""

    schema_version: int = 1
    entry_id: str
    session_id: str
    session_digest: str
    archived_at: datetime
    authoritative: bool = False
    evidence_only: bool = True

    @field_validator("entry_id", "session_id")
    @classmethod
    def _identifier_present(cls, value: str, info: object) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError(f"{getattr(info, 'field_name', 'identifier')} cannot be empty")
        return normalized

    @field_validator("session_digest")
    @classmethod
    def _digest(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("session_digest must be a SHA-256 hex digest")
        return normalized

    @field_validator("archived_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("archived_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _consistent(self) -> "ObservationArchiveEntry":
        if self.schema_version != 1:
            raise ValueError("unsupported archive entry schema version")
        if self.authoritative or not self.evidence_only:
            raise ValueError("archive entries must remain evidence-only")
        expected = self._compute_entry_id(self._identity_payload())
        if not hmac.compare_digest(self.entry_id, expected):
            raise ValueError("entry identifier does not match canonical archive metadata")
        return self

    def _identity_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"entry_id"})

    @staticmethod
    def _compute_entry_id(payload: dict[str, Any]) -> str:
        body = canonical_json({"domain": _ENTRY_DOMAIN, "entry": payload})
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        session: ObservationSession,
        *,
        archived_at: datetime,
    ) -> "ObservationArchiveEntry":
        """Wrap a sealed observation session into an archive entry."""
        if session.lifecycle != ObservationSessionLifecycle.SEALED:
            raise ValueError("only sealed observation sessions can be archived")

        payload = {
            "schema_version": 1,
            "session_id": session.session_id,
            "session_digest": session.digest,
            "archived_at": archived_at,
            "authoritative": False,
            "evidence_only": True,
        }
        identity = cls.model_construct(entry_id="", **payload)._identity_payload()
        return cls(entry_id=cls._compute_entry_id(identity), **payload)

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
