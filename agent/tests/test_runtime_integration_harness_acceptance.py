"""Level 19 acceptance tests for the read-only runtime integration harness."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.aios.runtime_adapter import AdapterRegistry, CanonicalRuntimeAdapter, RuntimeEvent
from src.aios.runtime_harness import RuntimeIntegrationHarness

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)


def _raw_event(sequence_id: int = 1) -> dict[str, object]:
    return {
        "event_id": f"event-{sequence_id}",
        "event_type": "runtime-observation",
        "source_id": "runtime-observer",
        "sequence_id": sequence_id,
        "occurred_at": NOW + timedelta(seconds=sequence_id),
        "payload": {"health": "healthy", "count": sequence_id},
    }


def test_harness_session_lifecycle_is_immutable_and_deterministic() -> None:
    harness = RuntimeIntegrationHarness(CanonicalRuntimeAdapter())
    first = harness.ingest((_raw_event(1), _raw_event(2)), opened_at=NOW)
    second = harness.ingest((_raw_event(1), _raw_event(2)), opened_at=NOW)

    assert first.session.session_id == second.session.session_id
    assert first.session.opened_at == NOW
    assert first.session.expected_event_count == 2
    assert first.session.execution_authority == "existing-runtime"
    assert first.session.evidence_only is True
    assert first.canonical_json() == second.canonical_json()
    assert first.digest == second.digest
    with pytest.raises(ValidationError):
        first.session.session_id = "changed"  # type: ignore[misc]


def test_runtime_event_ingestion_and_adapter_integration() -> None:
    report = RuntimeIntegrationHarness(CanonicalRuntimeAdapter()).ingest(
        (_raw_event(1), RuntimeEvent(**_raw_event(2))), opened_at=NOW
    )

    assert report.accepted_count == 2
    assert report.rejected_count == 0
    assert report.validation_failure_count == 0
    assert report.conversion_count == 2
    assert tuple(item.input_index for item in report.outcomes) == (0, 1)
    assert all(item.accepted for item in report.outcomes)
    assert tuple(item.sequence_id for item in report.accepted_events) == (1, 2)
    assert all(item.verify().verified for item in report.accepted_evidence)
    assert tuple(item.attributes["sequence_id"] for item in report.accepted_evidence) == (1, 2)


def test_harness_records_rejected_events_and_validation_failures() -> None:
    malformed = _raw_event(2)
    malformed["occurred_at"] = "not-a-timestamp"
    duplicate = _raw_event(1)
    duplicate["event_id"] = "duplicate-event"
    report = RuntimeIntegrationHarness(CanonicalRuntimeAdapter()).ingest(
        (_raw_event(1), malformed, duplicate), opened_at=NOW
    )

    assert report.accepted_count == 1
    assert report.rejected_count == 2
    assert report.validation_failure_count == 2
    assert report.conversion_count == 1
    assert tuple(item.accepted for item in report.outcomes) == (True, False, False)
    assert all(item.error_kind == "validation" for item in report.outcomes[1:])
    assert "duplicate runtime event sequence identifier" in report.outcomes[2].error_message


def test_harness_records_adapter_conversion_failure_without_aborting_batch() -> None:
    class SelectiveAdapter(CanonicalRuntimeAdapter):
        adapter_id = "selective-runtime-event"

        def adapt(self, event: RuntimeEvent):  # type: ignore[no-untyped-def]
            if event.sequence_id == 2:
                raise TypeError("unsupported external event")
            return super().adapt(event)

    report = RuntimeIntegrationHarness(SelectiveAdapter()).ingest(
        (_raw_event(1), _raw_event(2), _raw_event(3)), opened_at=NOW
    )
    assert report.accepted_count == 2
    assert report.rejected_count == 1
    assert report.validation_failure_count == 0
    assert report.outcomes[1].error_kind == "conversion"
    assert report.conversion_count == 2


def test_replay_harness_consistency() -> None:
    harness = RuntimeIntegrationHarness(CanonicalRuntimeAdapter())
    report = harness.ingest((_raw_event(1), _raw_event(2), _raw_event(3)), opened_at=NOW)
    replay = harness.replay(report)

    assert replay.session_id == report.session.session_id
    assert replay.adapter_id == harness.adapter_id
    assert replay.compared_count == 3
    assert replay.matched_count == 3
    assert replay.identical is True
    assert replay.differences == ()
    assert replay.canonical_json() == harness.replay(report).canonical_json()


def test_replay_rejects_report_from_different_adapter() -> None:
    class AlternateAdapter(CanonicalRuntimeAdapter):
        adapter_id = "alternate-runtime-event"

    report = RuntimeIntegrationHarness(CanonicalRuntimeAdapter()).ingest((_raw_event(1),), opened_at=NOW)
    with pytest.raises(ValueError, match="does not match"):
        RuntimeIntegrationHarness(AlternateAdapter()).replay(report)


def test_harness_report_determinism_includes_input_order() -> None:
    harness = RuntimeIntegrationHarness(CanonicalRuntimeAdapter())
    ordered = harness.ingest((_raw_event(1), _raw_event(2)), opened_at=NOW)
    reversed_report = harness.ingest((_raw_event(2), _raw_event(1)), opened_at=NOW)
    assert ordered.canonical_json() != reversed_report.canonical_json()
    assert ordered.session.session_id != reversed_report.session.session_id
    assert ordered.canonical_json() == harness.ingest((_raw_event(1), _raw_event(2)), opened_at=NOW).canonical_json()


def test_multi_adapter_compatibility_through_registry() -> None:
    class AlternateAdapter(CanonicalRuntimeAdapter):
        adapter_id = "alternate-runtime-event"

    registry = AdapterRegistry()
    registry.register(CanonicalRuntimeAdapter())
    registry.register(AlternateAdapter())
    reports = tuple(
        RuntimeIntegrationHarness(adapter).ingest((_raw_event(1),), opened_at=NOW)
        for adapter in registry.list()
    )
    assert tuple(report.session.adapter_id for report in reports) == (
        "alternate-runtime-event",
        "canonical-runtime-event",
    )
    assert all(report.accepted_count == 1 for report in reports)
    assert all(report.accepted_evidence[0].verify().verified for report in reports)
    assert all(RuntimeIntegrationHarness(adapter).replay(report).identical for adapter, report in zip(registry.list(), reports))


def test_harness_rejects_naive_session_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        RuntimeIntegrationHarness(CanonicalRuntimeAdapter()).ingest(
            (_raw_event(1),), opened_at=datetime(2026, 7, 31, 12, 0)
        )


def test_level19_import_boundary_and_no_authority_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aios" / "runtime_harness"
    allowed = (
        "src.aios.contracts.identifiers",
        "src.aios.provenance",
        "src.aios.runtime_adapter",
        "src.aios.runtime_harness",
    )
    forbidden_import_parts = {
        "agent", "swarm", "live", "tools", "providers", "trading", "frontend", "api",
        "deployments", "experiments", "broker", "exchange", "scheduler", "migration",
    }
    forbidden_api_names = {
        "execute", "trade", "submit_order", "place_order", "schedule", "persist", "migrate",
        "enforce", "sign", "transfer_authority", "start_shadow_mode", "mutate_runtime",
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
