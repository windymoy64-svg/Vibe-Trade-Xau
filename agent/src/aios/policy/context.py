"""Immutable policy evaluation input."""
from __future__ import annotations
import hashlib, json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any
from pydantic import Field, field_serializer, field_validator
from src.aios.contracts.identifiers import FrozenContract


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"policy attributes contain non-JSON value: {type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


class PolicyContext(FrozenContract):
    subject: str
    action: str
    attributes: Mapping[str, Any] = Field(default_factory=dict)
    legacy_decision: str | None = None

    @field_validator("attributes")
    @classmethod
    def _immutable_attributes(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _freeze(value)

    @field_serializer("attributes")
    def _serialize_attributes(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _thaw(value)

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @property
    def subject_digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()