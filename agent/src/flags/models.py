"""Immutable feature-flag contracts."""
from __future__ import annotations
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from pydantic import Field, field_serializer, field_validator
from src.aios.contracts.identifiers import FrozenContract


class FlagState(str, Enum):
    OFF = "off"
    ON = "on"


class FlagKind(str, Enum):
    RISK = "risk"
    GENERAL = "general"


class FeatureFlag(FrozenContract):
    name: str
    state: FlagState = FlagState.OFF
    kind: FlagKind = FlagKind.GENERAL
    priority: int = 0
    metadata: Mapping[str, str] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def _freeze_metadata(cls, value: Mapping[str, str]) -> Mapping[str, str]:
        return MappingProxyType(dict(value))

    @field_serializer("metadata")
    def _serialize_metadata(self, value: Mapping[str, str]) -> dict[str, str]:
        return dict(value)