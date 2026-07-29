"""Immutable, independently verifiable content-addressed evidence."""
from __future__ import annotations
import hashlib, hmac
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
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
    raise ValueError(f"evidence attributes contain non-JSON value: {type(value).__name__}")


class EvidenceVerification(FrozenContract):
    """Deterministic result of comparing evidence content to its sealed digest."""

    evidence_id: str
    expected_digest: str
    computed_digest: str
    verified: bool
    reason: str

    def canonical_json(self) -> str:
        return canonical_json(self)


class EvidenceRecord(FrozenContract):
    evidence_id: str
    evidence_type: str
    issuer_id: str
    observed_at: datetime
    subject_digest: str
    references: tuple[str, ...] = ()
    attributes: Mapping[str, Any] = Field(default_factory=dict)
    expected_digest: str

    @field_validator("observed_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("subject_digest", "expected_digest")
    @classmethod
    def _sha256_digest(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("digest must be a lowercase SHA-256 hex digest")
        return normalized

    @field_validator("issuer_id", mode="before")
    @classmethod
    def _issuer_identifier(cls, value: str) -> str:
        from src.aios.contracts.identifiers import validate_identifier_segment

        return validate_identifier_segment(value, field_name="issuer_id")

    @field_validator("attributes")
    @classmethod
    def _immutable_attributes(cls, value: Mapping[str, Any]) -> Mapping[str, Any]:
        return _freeze(value)

    @field_serializer("attributes")
    def _serialize_attributes(self, value: Mapping[str, Any]) -> dict[str, Any]:
        def thaw(item: Any) -> Any:
            if isinstance(item, Mapping):
                return {key: thaw(child) for key, child in item.items()}
            if isinstance(item, tuple):
                return [thaw(child) for child in item]
            return item

        return thaw(value)

    def canonical_json(self) -> str:
        """Serialize evidence content without its externally supplied seal."""
        return canonical_json(self.model_dump(mode="json", exclude={"expected_digest"}))

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def verify(self) -> EvidenceVerification:
        """Compare canonical content against the independently supplied digest."""
        computed = self.digest
        verified = hmac.compare_digest(computed, self.expected_digest)
        return EvidenceVerification(
            evidence_id=self.evidence_id,
            expected_digest=self.expected_digest,
            computed_digest=computed,
            verified=verified,
            reason="digest verified" if verified else "computed digest does not match expected digest",
        )