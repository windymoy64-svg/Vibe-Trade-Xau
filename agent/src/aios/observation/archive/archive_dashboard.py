"""Read-only projections for observation archive evidence."""
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.archive.batch import ObservationArchiveBatch
from src.aios.observation.archive.chain import AuditChain
from src.aios.observation.archive.verification import verify_archive_integrity
from src.aios.provenance.serialization import canonical_json


class ArchiveHealth(str, Enum):
    HEALTHY = "healthy"
    EMPTY = "empty"
    DEGRADED = "degraded"


class ArchiveDashboard(FrozenContract):
    """Immutable summary that observes evidence and grants no authority."""

    schema_version: int = 1
    archive_count: int
    batch_count: int
    chain_integrity: bool
    replay_coverage: int
    archive_health: ArchiveHealth
    authoritative: bool = False
    evidence_only: bool = True
    execution_authority: str = "existing-runtime"

    @field_validator("archive_count", "batch_count", "replay_coverage")
    @classmethod
    def _valid_metric(cls, value: int, info: object) -> int:
        if value < 0 or (getattr(info, "field_name", "") == "replay_coverage" and value > 100):
            raise ValueError("archive dashboard metric is outside its valid range")
        return value

    @model_validator(mode="after")
    def _evidence_only(self) -> "ArchiveDashboard":
        if self.authoritative or not self.evidence_only or self.execution_authority != "existing-runtime":
            raise ValueError("archive dashboards must remain evidence-only")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)


def build_archive_dashboard(
    batches: Iterable[ObservationArchiveBatch],
    chain: AuditChain,
    *,
    replayed_entry_ids: Iterable[str] = (),
    expected_batch_ids: Iterable[str] | None = None,
) -> ArchiveDashboard:
    """Derive counts, replay coverage, chain integrity, and archive health."""
    items = tuple(batches)
    verification = verify_archive_integrity(items, chain, expected_batch_ids=expected_batch_ids)
    entry_ids = {entry.entry_id for batch in items for entry in batch.entries}
    replayed = set(replayed_entry_ids)
    coverage = (len(entry_ids & replayed) * 100 // len(entry_ids)) if entry_ids else 0
    if not verification.archive_valid:
        health = ArchiveHealth.DEGRADED
    elif not items:
        health = ArchiveHealth.EMPTY
    elif coverage == 100:
        health = ArchiveHealth.HEALTHY
    else:
        health = ArchiveHealth.DEGRADED
    return ArchiveDashboard(
        archive_count=verification.archive_count,
        batch_count=verification.batch_count,
        chain_integrity=verification.chain_integrity,
        replay_coverage=coverage,
        archive_health=health,
    )
