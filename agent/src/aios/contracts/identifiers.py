"""Stable, immutable identifiers shared by AIOS foundation contracts."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

_SEGMENT_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


class FrozenContract(BaseModel):
    """Base configuration for deterministic, side-effect-free contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


def validate_identifier_segment(value: str, *, field_name: str) -> str:
    """Normalize and validate one portable identifier segment."""
    normalized = value.strip().lower()
    if not _SEGMENT_RE.fullmatch(normalized):
        raise ValueError(
            f"{field_name} must start with a letter and contain only lowercase "
            "letters, digits, dots, underscores, or hyphens"
        )
    return normalized


class ResourceId(FrozenContract):
    """A stable, namespaced identity independent of storage location."""

    kind: str
    namespace: str
    name: str

    @field_validator("kind", "namespace", "name", mode="before")
    @classmethod
    def _normalize_segments(cls, value: Any, info: Any) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{info.field_name} must be a string")
        return validate_identifier_segment(value, field_name=info.field_name)

    @property
    def canonical(self) -> str:
        """Return the portable canonical representation."""
        return f"{self.kind}:{self.namespace}/{self.name}"

    def __str__(self) -> str:
        return self.canonical


class CorrelationId(FrozenContract):
    """Externally supplied correlation identifier."""

    value: str

    @field_validator("value")
    @classmethod
    def _validate_value(cls, value: str) -> str:
        return validate_identifier_segment(value, field_name="value")
