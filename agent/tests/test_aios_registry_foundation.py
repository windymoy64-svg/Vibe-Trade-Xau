"""Phase 0/1 acceptance tests for AIOS contracts and generic registry core."""

from __future__ import annotations

import ast
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.aios.contracts.compatibility import CompatibilitySpec
from src.aios.contracts.environment import ExecutionEnvironment
from src.aios.contracts.identifiers import ResourceId
from src.aios.contracts.lifecycle import (
    ArtifactLifecycle,
    RuntimeLifecycle,
    validate_artifact_transition,
    validate_runtime_transition,
)
from src.aios.contracts.ownership import Ownership
from src.registries.core.compatibility import validate_record_compatibility
from src.registries.core.errors import (
    CorruptRegistryError,
    DuplicateRecordError,
    IncompatibleRecordError,
)
from src.registries.core.file_store import FileRegistryStore
from src.registries.core.memory_store import MemoryRegistryStore
from src.registries.core.records import RegistryKey, RegistryRecord
from src.registries.core.store import RegistryStore
from src.registries.core.versions import SemanticVersion


def _record(*, name: str = "sample", version: str = "1.0.0") -> RegistryRecord:
    return RegistryRecord(
        key=RegistryKey(
            resource=ResourceId(kind="component", namespace="core", name=name),
            version=SemanticVersion(version),
        ),
        ownership=Ownership(
            technical_owner="platform-team",
            business_owner="product-team",
        ),
        compatibility=CompatibilitySpec(
            api_version="1.2.0",
            supported_environments=(ExecutionEnvironment.RESEARCH,),
        ),
        created_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        created_by=ResourceId(kind="actor", namespace="platform", name="builder"),
        labels=(("criticality", "low"),),
        metadata={"enabled": True, "count": 2},
    )


def test_identifier_is_normalized_stable_and_serializable() -> None:
    first = ResourceId(kind=" Component ", namespace=" Core ", name=" Alpha-One ")
    second = ResourceId(kind="component", namespace="core", name="alpha-one")
    assert first == second
    assert first.canonical == "component:core/alpha-one"
    assert ResourceId.model_validate_json(first.model_dump_json()) == first


def test_identifier_rejects_unportable_values() -> None:
    with pytest.raises(ValidationError):
        ResourceId(kind="component", namespace="../core", name="alpha")


def test_contracts_and_nested_metadata_are_immutable() -> None:
    record = _record()
    with pytest.raises(ValidationError):
        record.lifecycle = ArtifactLifecycle.ACTIVE  # type: ignore[misc]
    with pytest.raises(TypeError):
        record.metadata["enabled"] = False


def test_record_serialization_and_digest_are_deterministic() -> None:
    first = _record()
    second = _record()
    assert first.canonical_json() == second.canonical_json()
    assert first.content_digest() == second.content_digest()
    sealed = first.sealed()
    assert sealed.digest == first.content_digest()
    assert RegistryRecord.model_validate_json(sealed.model_dump_json()) == sealed


def test_tampered_digest_is_rejected() -> None:
    payload = _record().sealed().model_dump(mode="json")
    payload["metadata"]["count"] = 99
    with pytest.raises(ValidationError, match="digest does not match"):
        RegistryRecord.model_validate(payload)


def test_lifecycle_validation() -> None:
    validate_artifact_transition(ArtifactLifecycle.DRAFT, ArtifactLifecycle.VALIDATED)
    validate_runtime_transition(RuntimeLifecycle.REQUESTED, RuntimeLifecycle.AUTHENTICATED)
    with pytest.raises(ValueError, match="invalid artifact"):
        validate_artifact_transition(ArtifactLifecycle.DRAFT, ArtifactLifecycle.ACTIVE)
    with pytest.raises(ValueError, match="invalid runtime"):
        validate_runtime_transition(RuntimeLifecycle.REQUESTED, RuntimeLifecycle.RUNNING)


def test_semantic_version_validation_and_ordering() -> None:
    assert SemanticVersion("1.2.3-alpha.1") < SemanticVersion("1.2.3")
    assert SemanticVersion("1.2.3") < SemanticVersion("2.0.0")
    with pytest.raises(ValueError):
        SemanticVersion("latest")


def test_compatibility_validation() -> None:
    record = _record()
    validate_record_compatibility(
        record,
        environment=ExecutionEnvironment.RESEARCH,
        api_version=SemanticVersion("1.9.0"),
    )
    with pytest.raises(IncompatibleRecordError):
        validate_record_compatibility(
            record,
            environment=ExecutionEnvironment.LIVE,
            api_version=SemanticVersion("1.9.0"),
        )
    with pytest.raises(IncompatibleRecordError):
        validate_record_compatibility(
            record,
            environment=ExecutionEnvironment.RESEARCH,
            api_version=SemanticVersion("2.0.0"),
        )


@pytest.mark.parametrize("store_factory", [MemoryRegistryStore, lambda: FileRegistryStore(Path("unused"))])
def test_store_protocol_is_structural(store_factory) -> None:  # type: ignore[no-untyped-def]
    store = store_factory()
    assert isinstance(store, RegistryStore)


def test_memory_store_publish_retrieve_list_and_duplicate_rejection() -> None:
    store = MemoryRegistryStore()
    second = _record(name="beta")
    published = store.publish(_record())
    store.publish(second)
    assert published.digest is not None
    assert store.get(published.key) == published
    assert [item.key.resource.name for item in store.list()] == ["beta", "sample"]
    with pytest.raises(DuplicateRecordError):
        store.publish(_record())


def test_file_store_publish_retrieve_and_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "registry" / "records.json"
    store = FileRegistryStore(path)
    assert store.list() == ()
    published = store.publish(_record())
    assert FileRegistryStore(path).get(published.key) == published
    envelope = json.loads(path.read_text(encoding="utf-8"))
    assert envelope["schema_version"] == 1
    assert envelope["records"][0]["digest"] == published.digest
    with pytest.raises(DuplicateRecordError):
        store.publish(_record())


def test_file_store_uses_atomic_replace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = FileRegistryStore(tmp_path / "registry.json")
    calls: list[tuple[Path, Path]] = []
    real_replace = os.replace

    def observed_replace(source, target):  # type: ignore[no-untyped-def]
        calls.append((Path(source), Path(target)))
        return real_replace(source, target)

    monkeypatch.setattr("src.registries.core.file_store.os.replace", observed_replace)
    store.publish(_record())
    assert len(calls) == 1
    assert calls[0][0] != calls[0][1]
    assert calls[0][1] == store.path
    assert list(tmp_path.glob(".*.tmp")) == []


@pytest.mark.parametrize(
    "content",
    ["{not json", "[]", '{"schema_version":99,"records":[]}', '{"schema_version":1,"records":[{}]}'],
)
def test_file_store_detects_corrupt_records(tmp_path: Path, content: str) -> None:
    path = tmp_path / "registry.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(CorruptRegistryError):
        FileRegistryStore(path).list()


def test_foundation_import_boundary() -> None:
    root = Path(__file__).resolve().parents[1] / "src"
    packages = (root / "aios", root / "governance", root / "registries")
    forbidden = {
        "agent", "swarm", "live", "tools", "providers", "trading", "frontend",
        "api", "deployments", "experiments",
    }
    violations: list[str] = []
    for package in packages:
        for path in package.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    parts = name.split(".")
                    if parts[0] == "src" and len(parts) > 1 and parts[1] in forbidden:
                        violations.append(f"{path.relative_to(root)}: {name}")
    assert violations == []
