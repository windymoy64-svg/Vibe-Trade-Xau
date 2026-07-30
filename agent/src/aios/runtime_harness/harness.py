"""Pure ingestion and deterministic replay harness for runtime observations."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.serialization import canonical_json
from src.aios.runtime_adapter.adapter import RuntimeAdapter
from src.aios.runtime_adapter.contracts import RuntimeEvent
from src.aios.runtime_harness.contracts import (
    HarnessReport,
    HarnessSession,
    IngestionOutcome,
    ReplayHarnessResult,
)


class RuntimeIntegrationHarness:
    """Receive supplied events, record outcomes, and never affect the runtime."""

    read_only = True
    execution_authority = "existing-runtime"
    evidence_only = True

    def __init__(self, adapter: RuntimeAdapter) -> None:
        if not isinstance(adapter, RuntimeAdapter):
            raise TypeError("harness requires a RuntimeAdapter")
        if adapter.read_only is not True:
            raise ValueError("harness requires a read-only adapter")
        self._adapter = adapter

    @property
    def adapter_id(self) -> str:
        return self._adapter.adapter_id

    def ingest(self, events: Iterable[Any], *, opened_at: datetime) -> HarnessReport:
        captured = tuple(events)
        normalized_opened_at = self._normalize_timestamp(opened_at)
        event_models: list[RuntimeEvent] = []
        outcomes: list[IngestionOutcome] = []
        evidence: list[EvidenceRecord] = []
        seen_sequences: set[int] = set()

        for index, raw_event in enumerate(captured):
            try:
                event = raw_event if isinstance(raw_event, RuntimeEvent) else RuntimeEvent.model_validate(raw_event)
                if event.sequence_id in seen_sequences:
                    raise ValueError("duplicate runtime event sequence identifier")
                seen_sequences.add(event.sequence_id)
                converted = self._adapter.adapt(event)
                event_models.append(event)
                evidence.append(converted)
                outcomes.append(IngestionOutcome(
                    input_index=index,
                    accepted=True,
                    event_id=event.event_id,
                    sequence_id=event.sequence_id,
                    evidence_id=converted.evidence_id,
                    evidence_digest=converted.expected_digest,
                ))
            except (ValidationError, TypeError, ValueError) as exc:
                event_id, sequence_id = self._safe_identity(raw_event)
                outcomes.append(IngestionOutcome(
                    input_index=index,
                    accepted=False,
                    event_id=event_id,
                    sequence_id=sequence_id,
                    error_kind="validation" if isinstance(exc, (ValidationError, ValueError)) else "conversion",
                    error_message=str(exc),
                ))

        session_id = self._session_id(normalized_opened_at, tuple(event_models), tuple(outcomes))
        session = HarnessSession(
            session_id=session_id,
            adapter_id=self.adapter_id,
            opened_at=normalized_opened_at,
            expected_event_count=len(captured),
        )
        accepted_count = sum(item.accepted for item in outcomes)
        rejected_count = len(outcomes) - accepted_count
        validation_failures = sum(item.error_kind == "validation" for item in outcomes)
        return HarnessReport(
            session=session,
            outcomes=tuple(outcomes),
            accepted_events=tuple(event_models),
            accepted_evidence=tuple(evidence),
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            validation_failure_count=validation_failures,
            conversion_count=len(evidence),
        )

    def replay(self, report: HarnessReport) -> ReplayHarnessResult:
        if report.session.adapter_id != self.adapter_id:
            raise ValueError("replay report adapter does not match harness adapter")
        replayed = tuple(self._adapter.adapt(event) for event in report.accepted_events)
        original = tuple(item.canonical_json() for item in report.accepted_evidence)
        regenerated = tuple(item.canonical_json() for item in replayed)
        differences = tuple(
            f"evidence-{index}-mismatch" for index, (left, right) in enumerate(zip(original, regenerated)) if left != right
        )
        if len(original) != len(regenerated):
            differences += ("evidence-count-mismatch",)
        matched_count = sum(left == right for left, right in zip(original, regenerated))
        return ReplayHarnessResult(
            session_id=report.session.session_id,
            adapter_id=self.adapter_id,
            compared_count=max(len(original), len(regenerated)),
            matched_count=matched_count,
            identical=not differences,
            differences=differences,
        )

    @staticmethod
    def _normalize_timestamp(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("opened_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _safe_identity(raw_event: Any) -> tuple[str | None, int | None]:
        if isinstance(raw_event, dict):
            event_id = raw_event.get("event_id")
            sequence_id = raw_event.get("sequence_id")
            return (event_id if isinstance(event_id, str) else None, sequence_id if isinstance(sequence_id, int) else None)
        return (None, None)

    def _session_id(
        self,
        opened_at: datetime,
        events: tuple[RuntimeEvent, ...],
        outcomes: tuple[IngestionOutcome, ...],
    ) -> str:
        content = canonical_json({
            "adapter_id": self.adapter_id,
            "opened_at": opened_at.isoformat(),
            "events": events,
            "outcomes": outcomes,
        })
        return f"harness-{hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]}"
