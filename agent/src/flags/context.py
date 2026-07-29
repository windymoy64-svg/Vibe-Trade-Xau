"""Deterministic feature-flag evaluation context."""
from __future__ import annotations
from types import MappingProxyType
from typing import Mapping, Any
from pydantic import Field, field_serializer, field_validator
from src.aios.contracts.identifiers import FrozenContract


class FlagContext(FrozenContract):
    subject: str
    environment: str = "research"
    operation: str = "read"
    attributes: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("attributes")
    @classmethod
    def _freeze_attributes(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return MappingProxyType(dict(value))

    @field_serializer("attributes")
    def _serialize_attributes(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return dict(value)

    @property
    def is_write(self) -> bool:
        return self.operation.lower() in {"write", "execute", "trade", "live"}