"""Phase 11 acceptance tests for the observation archive and audit chain."""
from __future__ import annotations

import ast
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.aios.observation import ObservationSession, ObservationSessionLifecycle, build_evidence_pipeline
from src.aios.observation.archive import (
    ArchiveHealth,
    AuditChain,
    ObservationArchiveBatch,
    ObservationArchiveEntry,
    build_archive_batch,
    build_archive_dashboard,
    build_audit_chain,
    verify_archive_integrity,
)
from src.aios.provenance.authenticity import IssuerIdentity, RepositoryTrustedIssuerPolicy
from src.aios.provenance.evidence import EvidenceRecord
from src.aios.provenance.verification_manifest import VerificationManifest

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def _sealed_session(name: str, offset: int = 0) -> ObservationSession:
    observed_at = NOW + timedelta(seconds=offset)
    unsealed = EvidenceRecord.model_construct(
        evidence_id=f"evidence-{name}", evidence_type="runtime-observation",
        issuer_id="phase11-observer", observed_at=observed_at, subject_digest="a" * 64,
        references=(), attributes={"scope": "phase-11"}, expected_digest="",
    )
    evidence = EvidenceRecord(
        **unsealed.model_dump(exclude={"expected_digest"}),
        expected_digest=hashlib.sha256(unsealed.canonical_json().encode()).hexdigest(),
    )
    policy = RepositoryTrustedIssuerPolicy(
        policy_id="phase11-policy", version=1, effective_at=NOW - timedelta(days=1),
        expires_at=NOW + timedelta(days=1), issuers=(IssuerIdentity(
            issuer_id="phase11-observer", display_name="Phase Eleven Observer",
            trust_domain="repository", trusted=True,
        ),),
    )
    manifest = VerificationManifest.create(evidence, policy, verified_at=observed_at)
    pipeline = build_evidence_pipeline((("runtime-observer", manifest, 1),))
    return ObservationSession.create(
        lifecycle=ObservationSessionLifecycle.SEALED, opened_at=NOW,
        pipeline=pipeline, sealed_at=observed_at + timedelta(seconds=1),
    )


def _entry(name: str, offset: int = 0) -> ObservationArchiveEntry:
    return ObservationArchiveEntry.create(
        _sealed_session(name, offset), archived_at=NOW + timedelta(minutes=offset + 1)
    )


def _batches() -> tuple[ObservationArchiveBatch, ObservationArchiveBatch]:
    return (
        build_archive_batch((_entry("alpha"), _entry("beta", 1)), batched_at=NOW + timedelta(hours=1)),
        build_archive_batch((_entry("gamma", 2),), batched_at=NOW + timedelta(hours=2)),
    )


def test_archive_entry_is_immutable_and_deterministic() -> None:
    session = _sealed_session("one")
    first = ObservationArchiveEntry.create(session, archived_at=NOW + timedelta(minutes=1))
    second = ObservationArchiveEntry.create(session, archived_at=NOW + timedelta(minutes=1))
    assert first.entry_id == second.entry_id
    assert first.digest == second.digest
    with pytest.raises(ValidationError):
        first.session_id = "changed"  # type: ignore[misc]
    with pytest.raises(ValueError, match="only sealed"):
        ObservationArchiveEntry.create(
            ObservationSession.create(lifecycle=ObservationSessionLifecycle.OPENED, opened_at=NOW),
            archived_at=NOW,
        )


def test_batch_ordering_and_digest_are_stable() -> None:
    first, second = _entry("one"), _entry("two", 1)
    left = build_archive_batch((first, second), batched_at=NOW)
    right = build_archive_batch((second, first), batched_at=NOW)
    assert left.entries == right.entries
    assert left.batch_id == right.batch_id
    assert left.digest == right.digest
    with pytest.raises(ValueError, match="duplicate archive entry"):
        build_archive_batch((first, first), batched_at=NOW)


def test_audit_chain_verification_and_previous_batch_linkage() -> None:
    batches = _batches()
    chain = build_audit_chain(batches)
    assert chain.verify_integrity()
    assert chain.links[0].previous_batch_digest == "0" * 64
    assert chain.links[1].previous_batch_digest == batches[0].digest
    assert verify_archive_integrity(batches, chain).archive_valid


def test_missing_batch_is_detected() -> None:
    batches = _batches()
    result = verify_archive_integrity(batches[:1], build_audit_chain(batches))
    assert result.archive_valid is False
    assert result.omission_detected is True


def test_duplicate_batch_is_detected() -> None:
    batches = _batches()
    result = verify_archive_integrity((batches[0], batches[0]), build_audit_chain(batches))
    assert result.archive_valid is False
    assert result.duplication_detected is True
    with pytest.raises(ValueError, match="duplicate batch"):
        build_audit_chain((batches[0], batches[0]))


def test_batch_reordering_is_detected() -> None:
    batches = _batches()
    result = verify_archive_integrity(tuple(reversed(batches)), build_audit_chain(batches))
    assert result.archive_valid is False
    assert result.reordering_detected is True


def test_batch_corruption_is_detected_fail_closed() -> None:
    batches = _batches()
    corrupt_payload = batches[0].model_dump()
    corrupt_payload["entries"] = (batches[0].entries[0],)
    corrupt = ObservationArchiveBatch.model_construct(**corrupt_payload)
    result = verify_archive_integrity((corrupt, batches[1]), build_audit_chain(batches))
    assert result.archive_valid is False
    assert result.chain_integrity is False
    assert result.corruption_detected is True
    malformed_chain = AuditChain.model_construct(links=(object(),))
    assert verify_archive_integrity(batches, malformed_chain).corruption_detected is True


def test_archive_dashboard_is_consistent() -> None:
    batches = _batches()
    replayed = tuple(entry.entry_id for batch in batches for entry in batch.entries)
    dashboard = build_archive_dashboard(batches, build_audit_chain(batches), replayed_entry_ids=replayed)
    assert dashboard.archive_count == 3
    assert dashboard.batch_count == 2
    assert dashboard.chain_integrity is True
    assert dashboard.replay_coverage == 100
    assert dashboard.archive_health == ArchiveHealth.HEALTHY
    assert dashboard.execution_authority == "existing-runtime"
    assert dashboard.canonical_json() == build_archive_dashboard(
        batches, build_audit_chain(batches), replayed_entry_ids=replayed
    ).canonical_json()


def test_phase11_import_boundary_and_no_execution_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "aios" / "observation" / "archive"
    allowed_src_prefixes = (
        "src.aios.contracts.identifiers", "src.aios.provenance.serialization",
        "src.aios.observation.archive", "src.aios.observation.session",
    )
    violations: list[str] = []
    forbidden_api_names = {"execute", "trade", "submit_order", "schedule", "persist", "migrate", "sign"}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("src."):
                if not node.module.startswith(allowed_src_prefixes):
                    violations.append(f"{path.name}: {node.module}")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in forbidden_api_names:
                violations.append(f"{path.name}: forbidden API {node.name}")
    assert violations == []
