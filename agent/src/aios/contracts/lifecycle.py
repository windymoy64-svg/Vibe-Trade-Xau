"""Lifecycle states and deterministic transition validation."""

from __future__ import annotations

from enum import Enum


class ArtifactLifecycle(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    REVIEW = "review"
    APPROVED = "approved"
    STAGED = "staged"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    REVOKED = "revoked"


class RuntimeLifecycle(str, Enum):
    REQUESTED = "requested"
    AUTHENTICATED = "authenticated"
    RESOLVED = "resolved"
    POLICY_EVALUATED = "policy_evaluated"
    PROVISIONED = "provisioned"
    READY = "ready"
    RUNNING = "running"
    QUIESCING = "quiescing"
    COMPLETED = "completed"
    FAILED = "failed"
    HALTED = "halted"
    TIMED_OUT = "timed_out"
    ARCHIVED = "archived"


_ARTIFACT_TRANSITIONS: dict[ArtifactLifecycle, frozenset[ArtifactLifecycle]] = {
    ArtifactLifecycle.DRAFT: frozenset({ArtifactLifecycle.VALIDATED, ArtifactLifecycle.REVOKED}),
    ArtifactLifecycle.VALIDATED: frozenset({ArtifactLifecycle.REVIEW, ArtifactLifecycle.DRAFT, ArtifactLifecycle.REVOKED}),
    ArtifactLifecycle.REVIEW: frozenset({ArtifactLifecycle.APPROVED, ArtifactLifecycle.DRAFT, ArtifactLifecycle.REVOKED}),
    ArtifactLifecycle.APPROVED: frozenset({ArtifactLifecycle.STAGED, ArtifactLifecycle.DEPRECATED, ArtifactLifecycle.REVOKED}),
    ArtifactLifecycle.STAGED: frozenset({ArtifactLifecycle.ACTIVE, ArtifactLifecycle.DEPRECATED, ArtifactLifecycle.REVOKED}),
    ArtifactLifecycle.ACTIVE: frozenset({ArtifactLifecycle.DEPRECATED, ArtifactLifecycle.REVOKED}),
    ArtifactLifecycle.DEPRECATED: frozenset({ArtifactLifecycle.RETIRED, ArtifactLifecycle.REVOKED}),
    ArtifactLifecycle.RETIRED: frozenset({ArtifactLifecycle.REVOKED}),
    ArtifactLifecycle.REVOKED: frozenset(),
}

_RUNTIME_TRANSITIONS: dict[RuntimeLifecycle, frozenset[RuntimeLifecycle]] = {
    RuntimeLifecycle.REQUESTED: frozenset({RuntimeLifecycle.AUTHENTICATED, RuntimeLifecycle.FAILED}),
    RuntimeLifecycle.AUTHENTICATED: frozenset({RuntimeLifecycle.RESOLVED, RuntimeLifecycle.FAILED}),
    RuntimeLifecycle.RESOLVED: frozenset({RuntimeLifecycle.POLICY_EVALUATED, RuntimeLifecycle.FAILED}),
    RuntimeLifecycle.POLICY_EVALUATED: frozenset({RuntimeLifecycle.PROVISIONED, RuntimeLifecycle.FAILED, RuntimeLifecycle.HALTED}),
    RuntimeLifecycle.PROVISIONED: frozenset({RuntimeLifecycle.READY, RuntimeLifecycle.FAILED, RuntimeLifecycle.HALTED}),
    RuntimeLifecycle.READY: frozenset({RuntimeLifecycle.RUNNING, RuntimeLifecycle.FAILED, RuntimeLifecycle.HALTED}),
    RuntimeLifecycle.RUNNING: frozenset({RuntimeLifecycle.QUIESCING, RuntimeLifecycle.COMPLETED, RuntimeLifecycle.FAILED, RuntimeLifecycle.HALTED, RuntimeLifecycle.TIMED_OUT}),
    RuntimeLifecycle.QUIESCING: frozenset({RuntimeLifecycle.COMPLETED, RuntimeLifecycle.FAILED, RuntimeLifecycle.HALTED, RuntimeLifecycle.TIMED_OUT}),
    RuntimeLifecycle.COMPLETED: frozenset({RuntimeLifecycle.ARCHIVED}),
    RuntimeLifecycle.FAILED: frozenset({RuntimeLifecycle.ARCHIVED}),
    RuntimeLifecycle.HALTED: frozenset({RuntimeLifecycle.ARCHIVED}),
    RuntimeLifecycle.TIMED_OUT: frozenset({RuntimeLifecycle.ARCHIVED}),
    RuntimeLifecycle.ARCHIVED: frozenset(),
}


def validate_artifact_transition(current: ArtifactLifecycle, target: ArtifactLifecycle) -> None:
    """Raise when an artifact transition is not part of the frozen state graph."""
    if target not in _ARTIFACT_TRANSITIONS[current]:
        raise ValueError(f"invalid artifact lifecycle transition: {current.value} -> {target.value}")


def validate_runtime_transition(current: RuntimeLifecycle, target: RuntimeLifecycle) -> None:
    """Raise when a runtime transition is not part of the frozen state graph."""
    if target not in _RUNTIME_TRANSITIONS[current]:
        raise ValueError(f"invalid runtime lifecycle transition: {current.value} -> {target.value}")
