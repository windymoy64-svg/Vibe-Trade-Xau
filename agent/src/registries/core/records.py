"""Generic immutable registry records."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any

from pydantic import Field, field_serializer, field_validator, model_validator

from src.aios.contracts.compatibility import CompatibilitySpec
from src.aios.contracts.identifiers import FrozenContract, ResourceId
from src.aios.contracts.lifecycle import ArtifactLifecycle
from src.aios.contracts.ownership import Ownership
from src.governance.contracts.approvals import Approval
from src.registries.core.approvals import ApprovalRequirements
from src.registries.core.versions import SemanticVersion


def _freeze_json(value: Any) -> Any:
    """Recursively convert JSON containers to immutable equivalents."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"metadata contains non-JSON value of type {type(value).__name__}")


def _thaw_json(value: Any) -> Any:
    """Convert immutable JSON containers back to serialization primitives."""
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


class RegistryKey(FrozenContract):
    """Exact immutable key for one versioned registry record."""

    resource: ResourceId
    version: SemanticVersion

    @property
    def canonical(self) -> str:
        return f"{self.resource.canonical}@{self.version}"

    def __str__(self) -> str:
        return self.canonical


class RegistryRecord(FrozenContract):
    """Storage-agnostic record containing metadata but no domain behavior."""

    schema_version: int = Field(default=1, gt=0)
    key: RegistryKey
    lifecycle: ArtifactLifecycle = ArtifactLifecycle.DRAFT
    ownership: Ownership
    compatibility: CompatibilitySpec
    approval_requirements: ApprovalRequirements = ApprovalRequirements()
    approvals: tuple[Approval, ...] = ()
    created_at: datetime
    created_by: ResourceId
    labels: tuple[tuple[str, str], ...] = ()
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    digest: str | None = None

    @field_validator("created_at")
    @classmethod
    def _normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("labels")
    @classmethod
    def _validate_labels(cls, value: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        if tuple(sorted(value)) != value:
            raise ValueError("labels must be sorted for deterministic serialization")
        if len({key for key, _ in value}) != len(value):
            raise ValueError("label keys must be unique")
        return value

    @field_validator("metadata")
    @classmethod
    def _validate_metadata(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be JSON serializable") from exc
        return _freeze_json(value)

    @field_serializer("metadata")
    def _serialize_metadata(self, value: Mapping[str, Any]) -> dict[str, Any]:
        return _thaw_json(value)

    @field_validator("digest")
    @classmethod
    def _validate_digest(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
            raise ValueError("digest must be a lowercase SHA-256 hex digest")
        return normalized

    @model_validator(mode="after")
    def _verify_digest(self) -> "RegistryRecord":
        if self.digest is not None and self.digest != self.content_digest():
            raise ValueError("record digest does not match canonical content")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        """Return JSON-ready content excluding the self-referential digest."""
        return self.model_dump(mode="json", exclude={"digest"})

    def canonical_json(self) -> str:
        """Return byte-stable canonical JSON."""
        return json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def content_digest(self) -> str:
        """Return the SHA-256 digest of canonical record content."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def sealed(self) -> "RegistryRecord":
        """Return an immutable copy carrying its verified content digest."""
        return self.model_copy(update={"digest": self.content_digest()})
