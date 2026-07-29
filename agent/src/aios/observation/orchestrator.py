"""Observation orchestrator coordinating sources without execution capability."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from pydantic import model_validator

from src.aios.contracts.identifiers import FrozenContract
from src.aios.observation.pipeline import EvidencePipeline, build_evidence_pipeline
from src.aios.observation.session import ObservationSession, ObservationSessionLifecycle
from src.aios.observation.sources import ObservationSource
from src.aios.provenance.verification_manifest import VerificationManifest


class SourceSubmission(FrozenContract):
    """Caller-supplied observation batch from one source."""

    source: ObservationSource
    manifests: tuple[VerificationManifest, ...] = ()
    verification_latencies_ms: tuple[int, ...] = ()

    @model_validator(mode="after")
    def _aligned_latencies(self) -> "SourceSubmission":
        if len(self.verification_latencies_ms) not in {0, len(self.manifests)}:
            raise ValueError("verification latencies must align with submitted manifests")
        return self


class ObservationOrchestrator:
    """Coordinate observation sources into an evidence-only session."""

    mode = "observation-only"
    execution_authority = "existing-runtime"
    executable = False
    authoritative = False

    def coordinate(
        self,
        submissions: Iterable[SourceSubmission],
        *,
        opened_at: datetime,
        sealed_at: datetime,
    ) -> ObservationSession:
        """Build a sealed observation session from verified source submissions."""
        items = tuple(submissions)
        sources = tuple(item.source for item in items)
        source_ids = tuple(source.source_id for source in sources)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("observation sources must be unique")

        pipeline_inputs: list[tuple[str, VerificationManifest, int]] = []
        for item in items:
            latencies = item.verification_latencies_ms or tuple(0 for _ in item.manifests)
            for manifest, latency in zip(item.manifests, latencies, strict=True):
                pipeline_inputs.append((item.source.source_id, manifest, latency))

        pipeline = build_evidence_pipeline(pipeline_inputs)
        opened = ObservationSession.create(
            lifecycle=ObservationSessionLifecycle.OPENED,
            opened_at=opened_at,
            sources=sources,
        )
        collecting = opened.transition_to(
            ObservationSessionLifecycle.COLLECTING,
            sources=sources,
            pipeline=pipeline,
        )
        return collecting.transition_to(
            ObservationSessionLifecycle.SEALED,
            sources=sources,
            pipeline=pipeline,
            sealed_at=sealed_at,
        )

    def open_session(
        self,
        sources: Iterable[ObservationSource],
        *,
        opened_at: datetime,
    ) -> ObservationSession:
        """Open an empty observation session without collecting evidence yet."""
        return ObservationSession.create(
            lifecycle=ObservationSessionLifecycle.OPENED,
            opened_at=opened_at,
            sources=tuple(sources),
            pipeline=EvidencePipeline(),
        )
