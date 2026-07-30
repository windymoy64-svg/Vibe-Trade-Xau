"""Append-only, hash-linked JSONL event persistence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from src.trading.runtime_pipeline.contracts import PipelineStage, RuntimeEvent, _canonical_json


class RuntimeEventLog:
    """Persist a globally hash-linked immutable event chain."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._last: RuntimeEvent | None = None
        if self.path.exists():
            events = self.read_all()
            self.verify(events)
            self._last = events[-1] if events else None

    def append(self, stage: PipelineStage, candle_id: str, occurred_at, payload: Any) -> RuntimeEvent:  # type: ignore[no-untyped-def]
        serialized = _payload(payload)
        previous_id = self._last.event_id if self._last else None
        previous_hash = self._last.event_hash if self._last else None
        material = {
            "candle_id": candle_id,
            "occurred_at": occurred_at.isoformat(),
            "payload": serialized,
            "previous_event_id": previous_id,
            "previous_hash": previous_hash,
            "stage": stage.value,
        }
        event_hash = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
        event_id = hashlib.sha256(f"{event_hash}:event".encode("utf-8")).hexdigest()
        event = RuntimeEvent(
            event_id=event_id,
            previous_event_id=previous_id,
            stage=stage,
            candle_id=candle_id,
            occurred_at=occurred_at,
            payload=serialized,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(event.canonical_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._last = event
        return event

    def read_all(self) -> tuple[RuntimeEvent, ...]:
        if not self.path.exists():
            return ()
        with self.path.open("r", encoding="utf-8") as handle:
            return tuple(RuntimeEvent.model_validate_json(line) for line in handle if line.strip())

    @staticmethod
    def verify(events: tuple[RuntimeEvent, ...] | list[RuntimeEvent]) -> None:
        previous: RuntimeEvent | None = None
        for event in events:
            if event.previous_event_id != (previous.event_id if previous else None):
                raise ValueError("broken runtime event ID chain")
            if event.previous_hash != (previous.event_hash if previous else None):
                raise ValueError("broken runtime event hash chain")
            material = {
                "candle_id": event.candle_id,
                "occurred_at": event.occurred_at.isoformat(),
                "payload": event.payload,
                "previous_event_id": event.previous_event_id,
                "previous_hash": event.previous_hash,
                "stage": event.stage.value,
            }
            expected = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
            if event.event_hash != expected:
                raise ValueError("runtime event hash mismatch")
            if event.event_id != hashlib.sha256(f"{expected}:event".encode("utf-8")).hexdigest():
                raise ValueError("runtime event ID mismatch")
            previous = event


def _payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        serialized = TypeAdapter(dict[str, Any]).dump_python(value, mode="json")
        # Canonical round-trip rejects non-finite values and detaches nested mutable mappings.
        return json.loads(_canonical_json(serialized))
    raise TypeError("runtime event payload must be a model or mapping")