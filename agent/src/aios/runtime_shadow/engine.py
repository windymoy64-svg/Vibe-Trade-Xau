"""Pure comparison engine for runtime decisions and AIOS assessments."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import datetime, timezone

from src.aios.provenance.serialization import canonical_json
from src.aios.runtime_shadow.contracts import (
    AssessmentValue,
    ComparisonArtifact,
    ComparisonClassification,
    DecisionSnapshot,
    ShadowReport,
    ShadowSession,
)


class ShadowComparisonEngine:
    """Compare supplied snapshots without recommending or influencing behavior."""

    read_only = True
    execution_authority = "existing-runtime"
    evidence_only = True

    def __init__(self, session: ShadowSession) -> None:
        self.session = session

    def compare(self, snapshots: Iterable[DecisionSnapshot]) -> ShadowReport:
        captured = tuple(snapshots)
        if len({item.snapshot_id for item in captured}) != len(captured):
            raise ValueError("duplicate decision snapshot identifier")
        ordered_snapshots = tuple(sorted(captured, key=lambda item: item.snapshot_id))
        if _snapshot_set_digest(ordered_snapshots) != self.session.snapshot_set_digest:
            raise ValueError("decision snapshots do not match shadow session")
        artifacts = tuple(self._compare_one(item) for item in ordered_snapshots)
        counts = {classification: sum(item.classification == classification for item in artifacts)
                  for classification in ComparisonClassification}
        return ShadowReport(
            session=self.session,
            snapshots=ordered_snapshots,
            artifacts=artifacts,
            agreement_count=counts[ComparisonClassification.AGREEMENT],
            disagreement_count=counts[ComparisonClassification.DISAGREEMENT],
            indeterminate_count=counts[ComparisonClassification.INDETERMINATE],
        )

    def replay(self, report: ShadowReport) -> ShadowReport:
        if report.session != self.session:
            raise ValueError("shadow report session does not match comparison engine")
        return self.compare(report.snapshots)

    @staticmethod
    def _compare_one(snapshot: DecisionSnapshot) -> ComparisonArtifact:
        runtime = snapshot.runtime.value
        aios = snapshot.aios.value
        if AssessmentValue.UNKNOWN in (runtime, aios):
            classification = ComparisonClassification.INDETERMINATE
            reason = "at least one assessment is unknown"
        elif runtime == aios:
            classification = ComparisonClassification.AGREEMENT
            reason = "runtime and AIOS assessment values agree"
        else:
            classification = ComparisonClassification.DISAGREEMENT
            reason = "runtime and AIOS assessment values differ"
        return ComparisonArtifact(
            snapshot_id=snapshot.snapshot_id,
            evidence_id=snapshot.evidence_id,
            evidence_digest=snapshot.evidence_digest,
            classification=classification,
            runtime_value=runtime,
            aios_value=aios,
            reason=reason,
        )

def build_shadow_session(runtime_identity: str, adapter_id: str, opened_at: datetime, snapshots: Iterable[DecisionSnapshot]) -> ShadowSession:
    """Build a deterministic session descriptor from caller-supplied snapshots."""
    if opened_at.tzinfo is None or opened_at.utcoffset() is None:
        raise ValueError("opened_at must be timezone-aware")
    normalized = opened_at.astimezone(timezone.utc)
    snapshot_tuple = tuple(sorted(snapshots, key=lambda item: item.snapshot_id))
    snapshot_set_digest = _snapshot_set_digest(snapshot_tuple)
    content = canonical_json({
        "runtime_identity": runtime_identity,
        "adapter_id": adapter_id,
        "opened_at": normalized.isoformat(),
        "snapshots": snapshot_tuple,
    })
    session_id = f"shadow-{hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]}"
    return ShadowSession(
        session_id=session_id,
        runtime_identity=runtime_identity,
        adapter_id=adapter_id,
        opened_at=opened_at,
        snapshot_set_digest=snapshot_set_digest,
    )


def _snapshot_set_digest(snapshots: tuple[DecisionSnapshot, ...]) -> str:
    content = canonical_json(snapshots)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
