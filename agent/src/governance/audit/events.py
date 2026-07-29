"""Immutable, JSON-serializable governance audit events."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from pydantic import Field, field_serializer, field_validator
from src.aios.contracts.identifiers import FrozenContract
from src.aios.provenance.serialization import canonical_json


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"audit payload contains non-JSON value: {type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


class AuditEvent(FrozenContract):
    """One append-only observation; it carries no executable action."""
    event_id: str
    event_type: str
    occurred_at: datetime
    subject_digest: str
    payload: Mapping[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    schema_version: int = 1

    @field_validator("occurred_at")
    @classmethod
    def _utc_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("payload")
    @classmethod
    def _immutable_payload(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _freeze(value)

    @field_serializer("payload")
    def _serialize_payload(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _thaw(value)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AuditEvent":
        return cls.model_validate(dict(value))

    def canonical_json(self) -> str:
        return canonical_json(self)

    def content_digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def model_dump_json(self, **kwargs: Any) -> str:  # type: ignore[override]
        kwargs.setdefault("exclude_none", False)
        return super().model_dump_json(**kwargs)

    @property
    def utc_occurred_at(self) -> datetime:
        return self.occurred_at.astimezone(timezone.utc)