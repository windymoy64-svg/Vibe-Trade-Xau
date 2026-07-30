"""Level 18 acceptance tests for the read-only runtime adapter layer."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.aios.runtime_adapter import (
    AdapterRegistry,
    CanonicalRuntimeAdapter,
    ReplayAdapter,
    RuntimeAdapter,
    RuntimeEvent,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)


def _event(sequence_id: int = 1, *, occurred_at: datetime = NOW) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=f"event-{sequence_id}",
        event_type="runtime-observation",
        source_id="runtime-observer",
        sequence_id=sequence_id,
        occurred_at=occurred_at,
        payload={"health": "healthy", "metrics": {"count": sequence_id}, "tags": ["runtime"]},
    )


def test_runtime_event_mapping_produces_verified_canonical_evidence() -> None:
    event = _event()
    evidence = CanonicalRuntimeAdapter().adapt(event)

    assert evidence.evidence_id == "runtime-event-runtime-observer-1-event-1"
    assert evidence.evidence_type == "runtime-event"
    assert evidence.issuer_id == event.source_id
    assert evidence.observed_at == event.occurred_at
    assert evidence.subject_digest == event.digest
    assert evidence.attributes["sequence_id"] == 1
    assert evidence.attributes["execution_authority"] == "existing-runtime"
    assert evidence.attributes["evidence_only"] is True
    assert evidence.verify().verified is True


def test_runtime_event_is_immutable_and_normalizes_timestamp_to_utc() -> None:
    event = _event(occurred_at=datetime(2026, 7, 30, 14, 0, tzinfo=timezone(timedelta(hours=2))))
    assert event.occurred_at == NOW
    with pytest.raises(ValidationError):
        event.sequence_id = 2  # type: ignore[misc]
    with pytest.raises(TypeError):
        event.payload["health"] = "changed"  # type: ignore[index]
    with pytest.raises(TypeError):
        event.payload["metrics"]["count"] = 99  # type: ignore[index]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"event_id": ""}, "event_id"),
        ({"sequence_id": -1}, "sequence_id"),
        ({"occurred_at": datetime(2026, 7, 30, 12, 0)}, "timezone-aware"),
        ({"payload": {}}, "must not be empty"),
        ({"execution_authority": "adapter"}, "existing-runtime authority"),
        ({"evidence_only": False}, "evidence-only"),
    ],
)
def test_invalid_runtime_events_fail_closed(changes: dict[str, object], message: str) -> None:
    payload = _event().model_dump()
    payload.update(changes)
    with pytest.raises(ValidationError, match=message):
        RuntimeEvent(**payload)


def test_non_json_runtime_payload_fails_closed() -> None:
    with pytest.raises(ValidationError, match="non-JSON value"):
        RuntimeEvent(
            event_id="event-invalid",
            event_type="runtime-observation",
            source_id="runtime-observer",
            sequence_id=1,
            occurred_at=NOW,
            payload={"invalid": object()},
        )

    with pytest.raises(ValidationError, match="non-finite float"):
        RuntimeEvent(
            event_id="event-nan",
            event_type="runtime-observation",
            source_id="runtime-observer",
            sequence_id=2,
            occurred_at=NOW,
            payload={"invalid": float("nan")},
        )


def test_adapter_registry_is_structural_ordered_and_rejects_duplicates() -> None:
    class AlternateAdapter(CanonicalRuntimeAdapter):
        adapter_id = "alternate-runtime-event"

    registry = AdapterRegistry()
    canonical = CanonicalRuntimeAdapter()
    alternate = AlternateAdapter()

    assert isinstance(canonical, RuntimeAdapter)
    registry.register(canonical)
    registry.register(alternate)
    assert registry.get("canonical-runtime-event") is canonical
    assert tuple(adapter.adapter_id for adapter in registry.list()) == (
        "alternate-runtime-event",
        "canonical-runtime-event",
    )
    assert registry.read_only is True
    assert registry.execution_authority == "existing-runtime"
    with pytest.raises(ValueError, match="already registered"):
        registry.register(CanonicalRuntimeAdapter())


def test_adapter_registry_rejects_non_read_only_adapter() -> None:
    class UnsafeAdapter:
        adapter_id = "unsafe-adapter"
        read_only = False

        def adapt(self, event: RuntimeEvent):  # type: ignore[no-untyped-def]
            return event

    with pytest.raises(ValueError, match="must be read-only"):
        AdapterRegistry().register(UnsafeAdapter())


def test_replay_mapping_orders_by_sequence_and_preserves_timestamps() -> None:
    events = (
        _event(3, occurred_at=NOW + timedelta(seconds=3)),
        _event(1, occurred_at=NOW + timedelta(seconds=1)),
        _event(2, occurred_at=NOW + timedelta(seconds=2)),
    )
    evidence = ReplayAdapter(CanonicalRuntimeAdapter()).adapt_all(events)

    assert tuple(item.attributes["sequence_id"] for item in evidence) == (1, 2, 3)
    assert tuple(item.observed_at for item in evidence) == tuple(
        NOW + timedelta(seconds=sequence) for sequence in (1, 2, 3)
    )
    assert all(item.verify().verified for item in evidence)


def test_replay_rejects_duplicate_sequence_identifiers() -> None:
    first = _event(1)
    duplicate = RuntimeEvent(
        event_id="different-event",
        event_type=first.event_type,
        source_id=first.source_id,
        sequence_id=first.sequence_id,
        occurred_at=first.occurred_at + timedelta(seconds=1),
        payload={"health": "healthy"},
    )
    with pytest.raises(ValueError, match="duplicate runtime event sequence identifier"):
        ReplayAdapter(CanonicalRuntimeAdapter()).adapt_all((first, duplicate))


def test_adapter_outputs_are_deterministic_across_repeated_and_reversed_replay() -> None:
    events = (_event(1), _event(2, occurred_at=NOW + timedelta(seconds=1)))
    replay = ReplayAdapter(CanonicalRuntimeAdapter())
    first = replay.adapt_all(events)
    second = replay.adapt_all(reversed(events))
    assert tuple(item.canonical_json() for item in first) == tuple(item.canonical_json() for item in second)
    assert tuple(item.expected_digest for item in first) == tuple(item.expected_digest for item in second)


def test_level18_import_boundary_and_no_authority_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aios" / "runtime_adapter"
    allowed = (
        "src.aios.contracts.identifiers",
        "src.aios.provenance",
        "src.aios.runtime_adapter",
    )
    forbidden_import_parts = {
        "agent", "swarm", "live", "tools", "providers", "trading", "frontend", "api",
        "deployments", "experiments", "broker", "exchange", "scheduler", "migration",
    }
    forbidden_api_names = {
        "execute", "trade", "submit_order", "place_order", "schedule", "persist", "migrate",
        "enforce", "sign", "transfer_authority", "start_shadow_mode",
    }
    violations: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
                if node.module.startswith("src.") and not node.module.startswith(allowed):
                    violations.append(f"{path.name}: unapproved AIOS import {node.module}")
            for name in names:
                if forbidden_import_parts.intersection(name.split(".")):
                    violations.append(f"{path.name}: forbidden import {name}")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden_api_names:
                violations.append(f"{path.name}: forbidden API {node.name}")
    assert violations == []
