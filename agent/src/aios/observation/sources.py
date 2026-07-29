"""Immutable observation-source descriptors with no execution capability."""
from __future__ import annotations

from enum import Enum

from pydantic import field_validator

from src.aios.contracts.identifiers import FrozenContract, validate_identifier_segment
from src.aios.runtime.health import HealthState


class ObservationSourceKind(str, Enum):
    """Declared categories of observation producers."""

    RUNTIME = "runtime"
    PROVENANCE = "provenance"
    POLICY = "policy"
    TELEMETRY = "telemetry"
    EXTERNAL = "external"


class ObservationSource(FrozenContract):
    """Read-only description of one observation source."""

    source_id: str
    kind: ObservationSourceKind
    health: HealthState = HealthState.UNKNOWN
    detail: str = ""

    @field_validator("source_id", mode="before")
    @classmethod
    def _source_identifier(cls, value: str) -> str:
        return validate_identifier_segment(value, field_name="source_id")

    @property
    def healthy(self) -> bool:
        return self.health == HealthState.HEALTHY
