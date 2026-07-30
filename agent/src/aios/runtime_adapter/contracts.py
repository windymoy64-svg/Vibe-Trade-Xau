"""Immutable contracts for externally supplied runtime events."""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping

from pydantic import Field, field_serializer, field_validator

from src.aios.contracts.identifiers import FrozenContract, validate_identifier_segment
from src.aios.provenance.serialization import canonical_json


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("runtime event payload keys must be strings")
            frozen[key] = _freeze_json(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("runtime event payload contains non-finite float")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"runtime event payload contains non-JSON value: {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


class RuntimeEvent(FrozenContract):
    """One immutable observation emitted by the existing runtime."""

    event_id: str
    event_type: str
    source_id: str
    sequence_id: int = Field(ge=0)
    occurred_at: datetime
    payload: Mapping[str, Any]
    execution_authority: str = "existing-runtime"
    evidence_only: bool = True

    @field_validator("event_id", "event_type", "source_id", mode="before")
    @classmethod
    def _identifier(cls, value: str, info: Any) -> str:
        return validate_identifier_segment(value, field_name=info.field_name)

    @field_validator("occurred_at")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("payload")
    @classmethod
    def _immutable_payload(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        if not value:
            raise ValueError("runtime event payload must not be empty")
        return _freeze_json(value)

    @field_validator("execution_authority")
    @classmethod
    def _existing_runtime_authority(cls, value: str) -> str:
        if value != "existing-runtime":
            raise ValueError("runtime events must retain existing-runtime authority")
        return value

    @field_validator("evidence_only")
    @classmethod
    def _evidence_only(cls, value: bool) -> bool:
        if not value:
            raise ValueError("runtime events must remain evidence-only")
        return value

    @field_serializer("payload")
    def _serialize_payload(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _thaw_json(value)

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()
