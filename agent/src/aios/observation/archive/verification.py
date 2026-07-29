"""Fail-closed verification for immutable observation archives."""
from __future__ import annotations

import hmac
from collections.abc import Iterable

from pydantic import model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.archive.batch import ObservationArchiveBatch
from src.aios.observation.archive.chain import AuditChain
from src.aios.provenance.serialization import canonical_json


class ArchiveVerificationResult(FrozenContract):
    """Deterministic evidence describing all archive integrity outcomes."""

    schema_version: int = 1
    archive_valid: bool
    archive_count: int
    batch_count: int
    chain_integrity: bool
    omission_detected: bool
    duplication_detected: bool
    reordering_detected: bool
    corruption_detected: bool
    authoritative: bool = False
    evidence_only: bool = True

    @model_validator(mode="after")
    def _consistent(self) -> "ArchiveVerificationResult":
        if self.schema_version != 1 or self.archive_count < 0 or self.batch_count < 0:
            raise ValueError("invalid archive verification result")
        if self.authoritative or not self.evidence_only:
            raise ValueError("archive verification must remain evidence-only")
        failures = (
            self.omission_detected,
            self.duplication_detected,
            self.reordering_detected,
            self.corruption_detected,
        )
        if self.archive_valid != (self.chain_integrity and not any(failures)):
            raise ValueError("archive validity is inconsistent with verification outcomes")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)


def verify_archive_integrity(
    batches: Iterable[ObservationArchiveBatch],
    chain: AuditChain,
    *,
    expected_batch_ids: Iterable[str] | None = None,
) -> ArchiveVerificationResult:
    """Verify content, membership, and ordering without accessing storage."""
    try:
        supplied = tuple(batches)
        supplied_ids = tuple(batch.batch_id for batch in supplied)
        linked_ids = tuple(link.batch_id for link in chain.links)
        expected_ids = linked_ids if expected_batch_ids is None else tuple(expected_batch_ids)

        duplication = (
            len(set(supplied_ids)) != len(supplied_ids)
            or len(set(linked_ids)) != len(linked_ids)
            or len(set(expected_ids)) != len(expected_ids)
        )
        omission = len(supplied_ids) != len(expected_ids) or set(supplied_ids) != set(expected_ids)
        reordering = not omission and supplied_ids != expected_ids
        corruption = linked_ids != expected_ids or len(supplied) != len(chain.links)
        if not corruption:
            for batch, link in zip(supplied, chain.links, strict=True):
                if not hmac.compare_digest(batch.batch_id, link.batch_id) or not hmac.compare_digest(
                    batch.digest, link.batch_digest
                ):
                    corruption = True
                    break

        chain_integrity = chain.verify_integrity() and not corruption
        valid = chain_integrity and not any((omission, duplication, reordering, corruption))
        return ArchiveVerificationResult(
            archive_valid=valid,
            archive_count=sum(len(batch.entries) for batch in supplied),
            batch_count=len(supplied),
            chain_integrity=chain_integrity,
            omission_detected=omission,
            duplication_detected=duplication,
            reordering_detected=reordering,
            corruption_detected=corruption,
        )
    except Exception:  # noqa: BLE001 - malformed evidence must fail closed
        return ArchiveVerificationResult(
            archive_valid=False,
            archive_count=0,
            batch_count=0,
            chain_integrity=False,
            omission_detected=False,
            duplication_detected=False,
            reordering_detected=False,
            corruption_detected=True,
        )
