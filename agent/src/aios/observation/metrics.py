"""Deterministic observation metrics derived from sealed sessions."""
from __future__ import annotations

from collections.abc import Iterable

from pydantic import field_validator, model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.dashboard import observer_health_summary
from src.aios.observation.session import ObservationSession
from src.aios.provenance.serialization import canonical_json
from src.aios.runtime.health import HealthState


class ObservationMetrics(FrozenContract):
    """Immutable observation metrics with no execution side effects."""

    session_id: str
    verification_count: int
    average_verification_latency_ms: int
    max_verification_latency_ms: int
    replay_attempts: int
    replay_successes: int
    replay_success_rate: int
    evidence_expected: int
    evidence_present: int
    evidence_completeness_rate: int
    observer_health: HealthState
    healthy_source_ratio: int
    authoritative: bool = False
    evidence_only: bool = True

    @field_validator(
        "verification_count",
        "average_verification_latency_ms",
        "max_verification_latency_ms",
        "replay_attempts",
        "replay_successes",
        "replay_success_rate",
        "evidence_expected",
        "evidence_present",
        "evidence_completeness_rate",
        "healthy_source_ratio",
    )
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("metric values must be non-negative")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> "ObservationMetrics":
        if self.authoritative or not self.evidence_only:
            raise ValueError("observation metrics must remain evidence-only")
        if self.replay_successes > self.replay_attempts:
            raise ValueError("replay successes cannot exceed attempts")
        if self.evidence_present > self.evidence_expected and self.evidence_expected > 0:
            raise ValueError("present evidence cannot exceed expected evidence")
        for rate in (self.replay_success_rate, self.evidence_completeness_rate, self.healthy_source_ratio):
            if rate > 100:
                raise ValueError("percentage metrics cannot exceed 100")
        return self

    def canonical_json(self) -> str:
        return canonical_json(self)


def _percentage(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return int((numerator * 100) // denominator)


def aggregate_metrics(
    session: ObservationSession,
    *,
    replay_results: Iterable[bool] = (),
    evidence_expected: int | None = None,
) -> ObservationMetrics:
    """Aggregate verification latency, replay, completeness, and observer health."""
    entries = session.pipeline.entries
    latencies = tuple(entry.verification_latency_ms for entry in entries)
    average_latency = int(sum(latencies) // len(latencies)) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    results = tuple(replay_results)
    successes = sum(1 for result in results if result)
    present = len(entries)
    expected = present if evidence_expected is None else evidence_expected
    if expected < 0:
        raise ValueError("evidence_expected must be non-negative")
    healthy = sum(1 for source in session.sources if source.healthy)
    return ObservationMetrics(
        session_id=session.session_id,
        verification_count=len(entries),
        average_verification_latency_ms=average_latency,
        max_verification_latency_ms=max_latency,
        replay_attempts=len(results),
        replay_successes=successes,
        replay_success_rate=_percentage(successes, len(results)),
        evidence_expected=expected,
        evidence_present=present,
        evidence_completeness_rate=_percentage(min(present, expected), expected if expected else present or 1)
        if expected or present
        else 0,
        observer_health=observer_health_summary(session),
        healthy_source_ratio=_percentage(healthy, len(session.sources)),
    )
