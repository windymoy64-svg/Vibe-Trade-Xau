"""Deterministic audit chain linking archive batches by previous-batch digest."""
from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from typing import Any

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.archive.batch import ObservationArchiveBatch
from src.aios.provenance.serialization import canonical_json

_LINK_DOMAIN = "aios-audit-chain-link-v1"
_CHAIN_DOMAIN = "aios-audit-chain-v1"

_GENESIS_PREV_DIGEST = "0" * 64  # Sentinel: no previous batch

class AuditChainLink(FrozenContract):
    """Immutable link binding one archive batch to its predecessor."""

    schema_version: int = 1
    link_id: str
    sequence: int
    batch_id: str
    batch_digest: str
    previous_batch_digest: str
    authoritative: bool = False
    evidence_only: bool = True

    @field_validator("batch_digest", "previous_batch_digest")
    @classmethod
    def _hex_digest(cls, value: str, info: object) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError(f"{getattr(info, 'field_name', 'digest')} must be a SHA-256 hex digest")
        return normalized

    @field_validator("sequence")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("audit chain link sequence must be non-negative")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "AuditChainLink":
        if self.schema_version != 1:
            raise ValueError("unsupported audit chain link schema version")
        if self.authoritative or not self.evidence_only:
            raise ValueError("audit chain links must remain evidence-only")

        expected = self._compute_link_id(self._identity_payload())
        if not hmac.compare_digest(self.link_id, expected):
            raise ValueError("link identifier does not match canonical chain metadata")
        return self

    def _identity_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"link_id"})

    @staticmethod
    def _compute_link_id(payload: dict[str, Any]) -> str:
        body = canonical_json({"domain": _LINK_DOMAIN, "link": payload})
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        batch: ObservationArchiveBatch,
        *,
        sequence: int,
        previous_batch_digest: str,
    ) -> "AuditChainLink":
        payload = {
            "schema_version": 1,
            "sequence": sequence,
            "batch_id": batch.batch_id,
            "batch_digest": batch.digest,
            "previous_batch_digest": previous_batch_digest,
            "authoritative": False,
            "evidence_only": True,
        }
        identity = cls.model_construct(link_id="", **payload)._identity_payload()
        return cls(link_id=cls._compute_link_id(identity), **payload)

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

class AuditChain(FrozenContract):
    """Immutable deterministic audit chain over archive batches."""

    schema_version: int = 1
    links: tuple[AuditChainLink, ...] = ()
    authoritative: bool = False
    evidence_only: bool = True

    @model_validator(mode="after")
    def _consistent(self) -> "AuditChain":
        if self.schema_version != 1:
            raise ValueError("unsupported audit chain schema version")
        if self.authoritative or not self.evidence_only:
            raise ValueError("audit chains must remain evidence-only")

        # Validate contiguous sequences starting from 0
        sequences = tuple(link.sequence for link in self.links)
        if sequences != tuple(range(len(self.links))):
            raise ValueError("audit chain link sequences must be contiguous from zero")

        # Validate linkage
        for index, link in enumerate(self.links):
            if index == 0:
                if not hmac.compare_digest(link.previous_batch_digest, _GENESIS_PREV_DIGEST):
                    raise ValueError("first audit chain link must reference the genesis batch digest")
            else:
                expected_prev = self.links[index - 1].batch_digest
                if not hmac.compare_digest(link.previous_batch_digest, expected_prev):
                    raise ValueError(
                        f"audit chain broken at sequence {index}: "
                        "previous_batch_digest does not match the prior batch digest"
                    )
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)

    @property
    def head_digest(self) -> str | None:
        """Digest of the most recent link, or None for an empty chain."""
        if not self.links:
            return None
        return self.links[-1].digest

    def verify_integrity(self) -> bool:
        """Verify the full audit chain linkage. Fail-closed: False on any error."""
        try:
            if not self.links:
                return True
            for index, link in enumerate(self.links):
                if index == 0:
                    if link.sequence != index or not hmac.compare_digest(
                        link.previous_batch_digest, _GENESIS_PREV_DIGEST
                    ):
                        return False
                else:
                    prior_digest = self.links[index - 1].batch_digest
                    if link.sequence != index or not hmac.compare_digest(
                        link.previous_batch_digest, prior_digest
                    ):
                        return False
            return True
        except Exception:  # noqa: BLE001 — fail closed
            return False


def build_audit_chain(
    batches: Iterable[ObservationArchiveBatch],
) -> AuditChain:
    """Build a deterministic audit chain from an ordered sequence of batches."""
    ordered = tuple(batches)
    seen_batch_ids: set[str] = set()
    links: list[AuditChainLink] = []
    previous_batch_digest = _GENESIS_PREV_DIGEST

    for index, batch in enumerate(ordered):
        if batch.batch_id in seen_batch_ids:
            raise ValueError(f"duplicate batch in audit chain: {batch.batch_id}")
        seen_batch_ids.add(batch.batch_id)
        link = AuditChainLink.create(
            batch, sequence=index, previous_batch_digest=previous_batch_digest
        )
        links.append(link)
        previous_batch_digest = batch.digest

    return AuditChain(links=tuple(links))

