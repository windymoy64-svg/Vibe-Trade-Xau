"""Sprint 3 acceptance tests for strict canonical evidence serialization."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType

import pytest

from src.aios.provenance.serialization import canonical_json, canonicalize
from src.integration.runtime_snapshot import RuntimeSnapshot
from src.integration.shadow.report import render_report


def test_mapping_proxy_serialization_is_structural() -> None:
    value = MappingProxyType({"outer": MappingProxyType({"count": 2})})
    assert canonical_json(value) == '{"outer":{"count":2}}'


def test_nested_immutable_structures_become_json_containers() -> None:
    value = MappingProxyType({"rows": (MappingProxyType({"tags": ("a", "b")}),)})
    assert canonicalize(value) == {"rows": [{"tags": ["a", "b"]}]}


def test_canonical_ordering_is_stable() -> None:
    left = MappingProxyType({"z": 1, "a": MappingProxyType({"y": 2, "b": 3})})
    right = MappingProxyType({"a": MappingProxyType({"b": 3, "y": 2}), "z": 1})
    assert canonical_json(left) == canonical_json(right) == '{"a":{"b":3,"y":2},"z":1}'


def test_digest_is_stable_and_plain_json_compatible() -> None:
    payload = {"authority": "existing-runtime", "values": [1, 2], "valid": True}
    previous = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert canonical_json(payload) == previous
    assert hashlib.sha256(canonical_json(payload).encode()).hexdigest() == hashlib.sha256(previous.encode()).hexdigest()

    first = RuntimeSnapshot("snapshot-one", "2026-07-29T00:00:00Z", "existing-runtime", payload)
    second = RuntimeSnapshot("snapshot-one", "2026-07-29T00:00:00Z", "existing-runtime", dict(reversed(payload.items())))
    assert first.digest() == second.digest()


@dataclass
class MutableEvidence:
    value: str


@pytest.mark.parametrize("value", [{"bad": object()}, {1: "non-string-key"}, MutableEvidence("mutable"), float("nan")])
def test_unsupported_types_are_rejected(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        canonical_json(value)


def test_repeated_report_serialization_is_deterministic() -> None:
    report = MappingProxyType({"nested": MappingProxyType({"items": (3, 2, 1)})})
    first = render_report(report)
    second = render_report(report)
    assert first == second
    parsed = json.loads(first)
    digest = parsed.pop("report_digest")
    expected_body = canonical_json(parsed)
    assert digest == hashlib.sha256(expected_body.encode()).hexdigest()