"""Pure conversion of runtime-event observations into canonical evidence."""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable

from src.aios.provenance.evidence import EvidenceRecord
from src.aios.runtime_adapter.contracts import RuntimeEvent


@runtime_checkable
class RuntimeAdapter(Protocol):
    """Uniform read-only runtime-event conversion interface."""

    @property
    def adapter_id(self) -> str: ...

    @property
    def read_only(self) -> bool: ...

    def adapt(self, event: RuntimeEvent) -> EvidenceRecord:
        """Convert one already captured event without runtime access or mutation."""
        ...


class CanonicalRuntimeAdapter:
    """Deterministic evidence adapter for the certified AIOS pipeline."""

    adapter_id = "canonical-runtime-event"
    read_only = True
    execution_authority = "existing-runtime"
    evidence_only = True

    def adapt(self, event: RuntimeEvent) -> EvidenceRecord:
        if not isinstance(event, RuntimeEvent):
            raise TypeError("adapter input must be a validated RuntimeEvent")

        unsealed = EvidenceRecord.model_construct(
            evidence_id=f"runtime-event-{event.source_id}-{event.sequence_id}-{event.event_id}",
            evidence_type="runtime-event",
            issuer_id=event.source_id,
            observed_at=event.occurred_at,
            subject_digest=event.digest,
            references=(),
            attributes={
                "adapter_id": self.adapter_id,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "sequence_id": event.sequence_id,
                "payload": event.payload,
                "execution_authority": self.execution_authority,
                "evidence_only": self.evidence_only,
            },
            expected_digest="",
        )
        expected_digest = hashlib.sha256(unsealed.canonical_json().encode("utf-8")).hexdigest()
        return EvidenceRecord(
            **unsealed.model_dump(exclude={"expected_digest"}),
            expected_digest=expected_digest,
        )
