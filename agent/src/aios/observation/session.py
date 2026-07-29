"""Immutable observation sessions with deterministic identifiers."""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.pipeline import EvidencePipeline
from src.aios.observation.sources import ObservationSource
from src.aios.provenance.serialization import canonical_json

_SESSION_DOMAIN = "aios-observation-session-v1"


class ObservationSessionLifecycle(str, Enum):
    OPENED = "opened"
    COLLECTING = "collecting"
    SEALED = "sealed"
    ARCHIVED = "archived"


_SESSION_TRANSITIONS = {
    ObservationSessionLifecycle.OPENED: frozenset({ObservationSessionLifecycle.COLLECTING}),
    ObservationSessionLifecycle.COLLECTING: frozenset({ObservationSessionLifecycle.SEALED}),
    ObservationSessionLifecycle.SEALED: frozenset({ObservationSessionLifecycle.ARCHIVED}),
    ObservationSessionLifecycle.ARCHIVED: frozenset(),
}




class ObservationSession(FrozenContract):
    """Immutable evidence-only observation session."""

    schema_version: int = 1
    session_id: str
    lifecycle: ObservationSessionLifecycle
    opened_at: datetime
    sources: tuple[ObservationSource, ...] = ()
    pipeline: EvidencePipeline = EvidencePipeline()
    sealed_at: datetime | None = None
    authoritative: bool = False
    evidence_only: bool = True
    execution_authority: str = "existing-runtime"

    @field_validator("opened_at", "sealed_at")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _consistent(self) -> "ObservationSession":
        if self.schema_version != 1:
            raise ValueError("unsupported observation session schema version")
        if self.authoritative or not self.evidence_only:
            raise ValueError("observation sessions must remain evidence-only")
        if self.execution_authority != "existing-runtime":
            raise ValueError("observation sessions may not claim execution authority")
        source_ids = tuple(source.source_id for source in self.sources)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("observation session sources must be unique")
        sealed_states = {ObservationSessionLifecycle.SEALED, ObservationSessionLifecycle.ARCHIVED}
        if self.lifecycle in sealed_states:
            if self.sealed_at is None:
                raise ValueError("sealed observation sessions require sealed_at")
            if not self.pipeline.entries:
                raise ValueError("sealed observation sessions require verified evidence")
        if self.lifecycle not in sealed_states and self.sealed_at is not None:
            raise ValueError("unsealed observation sessions cannot record sealed_at")
        expected = self._compute_session_id(self._identity_payload())
        if not hmac.compare_digest(self.session_id, expected):
            raise ValueError("session identifier does not match canonical observation metadata")
        return self

    def _identity_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"session_id"})

    @staticmethod
    def _compute_session_id(payload: dict[str, Any]) -> str:
        body = canonical_json({"domain": _SESSION_DOMAIN, "session": payload})
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        *,
        lifecycle: ObservationSessionLifecycle,
        opened_at: datetime,
        sources: tuple[ObservationSource, ...] = (),
        pipeline: EvidencePipeline | None = None,
        sealed_at: datetime | None = None,
    ) -> "ObservationSession":
        payload = {
            "schema_version": 1,
            "lifecycle": lifecycle,
            "opened_at": opened_at,
            "sources": sources,
            "pipeline": pipeline or EvidencePipeline(),
            "sealed_at": sealed_at,
            "authoritative": False,
            "evidence_only": True,
            "execution_authority": "existing-runtime",
        }
        identity = cls.model_construct(session_id="", **payload)._identity_payload()
        return cls(session_id=cls._compute_session_id(identity), **payload)

    def transition_to(
        self,
        target: ObservationSessionLifecycle,
        *,
        pipeline: EvidencePipeline | None = None,
        sealed_at: datetime | None = None,
        sources: tuple[ObservationSource, ...] | None = None,
    ) -> "ObservationSession":
        """Return a new immutable session after a validated lifecycle transition."""
        validate_session_transition(self.lifecycle, target)
        next_pipeline = self.pipeline if pipeline is None else pipeline
        next_sources = self.sources if sources is None else sources
        next_sealed_at = self.sealed_at if sealed_at is None else sealed_at
        if target == ObservationSessionLifecycle.SEALED and next_sealed_at is None:
            raise ValueError("sealing an observation session requires sealed_at")
        return type(self).create(
            lifecycle=target,
            opened_at=self.opened_at,
            sources=next_sources,
            pipeline=next_pipeline,
            sealed_at=next_sealed_at,
        )

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

def validate_session_transition(
    current: ObservationSessionLifecycle, target: ObservationSessionLifecycle,
) -> None:
    if target not in _SESSION_TRANSITIONS[current]:
        raise ValueError(f"invalid observation session transition: {current.value} -> {target.value}")
