"""Read-only observation dashboard projections."""
from __future__ import annotations

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.session import ObservationSession, ObservationSessionLifecycle
from src.aios.provenance.serialization import canonical_json
from src.aios.runtime.health import HealthState


class ObservationDashboard(FrozenContract):
    """Immutable dashboard model derived from one observation session."""

    session_id: str
    lifecycle: ObservationSessionLifecycle
    readiness: bool
    authenticity_verified: bool
    provenance_complete: bool
    verification_count: int
    verified_count: int
    source_count: int
    healthy_source_count: int
    telemetry_states: tuple[tuple[str, str], ...] = ()
    authoritative: bool = False
    evidence_only: bool = True
    execution_authority: str = "existing-runtime"

    def canonical_json(self) -> str:
        return canonical_json(self)


def build_dashboard(session: ObservationSession) -> ObservationDashboard:
    """Project session state into a consistent read-only dashboard model."""
    entries = session.pipeline.entries
    verified = tuple(
        entry for entry in entries if entry.manifest.integrity_verified and entry.manifest.authentic
    )
    authenticity_verified = bool(entries) and len(verified) == len(entries)
    provenance_complete = authenticity_verified and len({entry.manifest.evidence_id for entry in entries}) == len(
        entries
    )
    healthy_sources = tuple(source for source in session.sources if source.healthy)
    sealed = session.lifecycle in {
        ObservationSessionLifecycle.SEALED,
        ObservationSessionLifecycle.ARCHIVED,
    }
    readiness = sealed and authenticity_verified and provenance_complete and bool(entries)
    telemetry = tuple(sorted((source.source_id, source.health.value) for source in session.sources))
    return ObservationDashboard(
        session_id=session.session_id,
        lifecycle=session.lifecycle,
        readiness=readiness,
        authenticity_verified=authenticity_verified,
        provenance_complete=provenance_complete,
        verification_count=len(entries),
        verified_count=len(verified),
        source_count=len(session.sources),
        healthy_source_count=len(healthy_sources),
        telemetry_states=telemetry,
    )


def observer_health_summary(session: ObservationSession) -> HealthState:
    """Aggregate source health without elevating observation into authority."""
    if not session.sources:
        return HealthState.UNKNOWN
    states = {source.health for source in session.sources}
    if HealthState.UNHEALTHY in states:
        return HealthState.UNHEALTHY
    if HealthState.DEGRADED in states or HealthState.UNKNOWN in states:
        return HealthState.DEGRADED
    return HealthState.HEALTHY
