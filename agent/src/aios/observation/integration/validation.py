"""Fail-closed cross-layer validation for Phase 13 artifacts."""
from __future__ import annotations

from src.aios.observation.archive.verification import verify_archive_integrity
from src.aios.observation.integration.contracts import IntegrationPipelineResult, IntegrationValidation


def validate_cross_layer(result: IntegrationPipelineResult) -> IntegrationValidation:
    findings: list[str] = []
    try:
        session_ids = tuple(item.session.session_id for item in result.sessions)
        if len(set(session_ids)) != len(session_ids):
            findings.append("duplicate-session-id")
        if tuple(item.metrics.session_id for item in result.sessions) != session_ids:
            findings.append("metrics-session-mismatch")
        if tuple(item.dashboard.session_id for item in result.sessions) != session_ids:
            findings.append("observation-dashboard-session-mismatch")
        if {item.archive_entry.session_id for item in result.sessions} != set(session_ids):
            findings.append("archive-session-coverage-mismatch")
        if len(result.archive_batch.entries) != len(result.sessions):
            findings.append("archive-entry-count-mismatch")
        manifest_ids = {item.manifest_id for item in result.manifests}
        pipeline_manifest_ids = {
            entry.manifest.manifest_id for item in result.sessions for entry in item.session.pipeline.entries
        }
        if manifest_ids != pipeline_manifest_ids:
            findings.append("manifest-coverage-mismatch")
        verification_count = sum(item.metrics.verification_count for item in result.sessions)
        if verification_count != len(result.manifests):
            findings.append("verification-count-mismatch")
        if result.analytics.quality.verification_count != verification_count:
            findings.append("analytics-verification-count-mismatch")
        if result.analytics.quality.session_count != len(result.sessions):
            findings.append("analytics-session-count-mismatch")
        recomputed_archive = verify_archive_integrity((result.archive_batch,), result.audit_chain)
        if recomputed_archive != result.archive_verification:
            findings.append("archive-verification-summary-mismatch")
        if not recomputed_archive.archive_valid:
            findings.append("archive-invalid")
        if not result.audit_chain.verify_integrity():
            findings.append("audit-chain-invalid")
        if result.dashboard.evidence_count != len(result.manifests):
            findings.append("integration-dashboard-evidence-count-mismatch")
        if result.dashboard.session_count != len(result.sessions):
            findings.append("integration-dashboard-session-count-mismatch")
        if result.dashboard.verification_count != verification_count:
            findings.append("integration-dashboard-verification-count-mismatch")
        if result.dashboard.archive_entry_count != len(result.archive_batch.entries):
            findings.append("integration-dashboard-archive-count-mismatch")
        if result.dashboard.batch_count != len(result.audit_chain.links):
            findings.append("integration-dashboard-batch-count-mismatch")
        if result.dashboard.archive_valid != recomputed_archive.archive_valid:
            findings.append("integration-dashboard-archive-status-mismatch")
        if result.dashboard.audit_chain_integrity != recomputed_archive.chain_integrity:
            findings.append("integration-dashboard-audit-integrity-mismatch")
        if result.dashboard.replay_coverage != result.analytics.replay.replay_coverage:
            findings.append("integration-dashboard-replay-mismatch")
    except Exception:  # noqa: BLE001 - malformed cross-layer artifacts fail closed
        findings.append("cross-layer-validation-error")
    return IntegrationValidation(valid=not findings, findings=tuple(sorted(set(findings))))
