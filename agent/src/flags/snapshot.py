"""Immutable feature-flag snapshots."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping
from pydantic import Field, field_serializer, field_validator
from src.aios.contracts.identifiers import FrozenContract
from src.flags.models import FeatureFlag


class FlagSnapshot(FrozenContract):
    snapshot_id: str
    captured_at: datetime
    flags: Mapping[str, FeatureFlag] = Field(default_factory=dict)
    source: str = "local"

    @field_validator("captured_at")
    @classmethod
    def _normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("flags")
    @classmethod
    def _freeze_flags(cls, value: Mapping[str, FeatureFlag]) -> Mapping[str, FeatureFlag]:
        return MappingProxyType(dict(value))

    @field_serializer("flags")
    def _serialize_flags(self, value: Mapping[str, FeatureFlag]) -> dict[str, FeatureFlag]:
        return dict(value)

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def utc_captured_at(self) -> datetime:
        return self.captured_at.astimezone(timezone.utc)