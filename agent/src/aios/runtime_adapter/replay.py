"""Deterministic conversion of caller-supplied historical runtime events."""

from __future__ import annotations

from collections.abc import Iterable

from src.aios.provenance.evidence import EvidenceRecord
from src.aios.runtime_adapter.adapter import RuntimeAdapter
from src.aios.runtime_adapter.contracts import RuntimeEvent


class ReplayAdapter:
    """Replay projection that performs no runtime reads, writes, or scheduling."""

    read_only = True
    execution_authority = "existing-runtime"
    evidence_only = True

    def __init__(self, adapter: RuntimeAdapter) -> None:
        if not isinstance(adapter, RuntimeAdapter):
            raise TypeError("replay adapter requires a RuntimeAdapter")
        if adapter.read_only is not True:
            raise ValueError("replay adapter requires a read-only adapter")
        self._adapter = adapter

    def adapt_all(self, events: Iterable[RuntimeEvent]) -> tuple[EvidenceRecord, ...]:
        captured = tuple(events)
        if any(not isinstance(event, RuntimeEvent) for event in captured):
            raise TypeError("replay input must contain only validated RuntimeEvent objects")

        sequence_ids = tuple(event.sequence_id for event in captured)
        if len(set(sequence_ids)) != len(sequence_ids):
            raise ValueError("duplicate runtime event sequence identifier")

        ordered = tuple(sorted(captured, key=lambda event: (event.sequence_id, event.occurred_at, event.event_id)))
        return tuple(self._adapter.adapt(event) for event in ordered)
