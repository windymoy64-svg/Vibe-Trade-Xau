"""Deterministic, default-off feature-flag evaluator."""
from __future__ import annotations
from datetime import timedelta
from typing import Mapping
from src.aios.contracts.identifiers import FrozenContract
from src.flags.context import FlagContext
from src.flags.models import FeatureFlag, FlagKind, FlagState
from src.flags.snapshot import FlagSnapshot
from src.flags.staleness import is_stale


class FlagEvaluation(FrozenContract):
    flag: str
    state: FlagState
    enabled: bool
    reason: str
    snapshot_id: str
    snapshot_digest: str
    stale: bool
    evidence_only: bool = True


def evaluate_flag(name: str, context: FlagContext, snapshot: FlagSnapshot, *, max_age: timedelta, now=None) -> FlagEvaluation:
    flag = snapshot.flags.get(name)
    stale = is_stale(snapshot, max_age=max_age, now=now)
    if stale and context.is_write:
        state, reason = FlagState.OFF, "stale-snapshot-fail-closed"
    elif flag is None:
        state, reason = FlagState.OFF, "missing-default-off"
    else:
        state, reason = flag.state, "configured"
    return FlagEvaluation(flag=name, state=state, enabled=state == FlagState.ON, reason=reason, snapshot_id=snapshot.snapshot_id, snapshot_digest=snapshot.digest, stale=stale)


def resolve_conflict(states: Mapping[str, FlagState]) -> FlagState:
    return FlagState.OFF if any(state == FlagState.OFF for state in states.values()) else (FlagState.ON if states else FlagState.OFF)


def resolve_precedence(flags: tuple[FeatureFlag, ...]) -> FlagState:
    """Resolve highest-priority declarations; equal-priority risk conflicts choose OFF."""
    if not flags:
        return FlagState.OFF
    highest = max(flag.priority for flag in flags)
    winners = tuple(flag for flag in flags if flag.priority == highest)
    if any(flag.kind == FlagKind.RISK and flag.state == FlagState.OFF for flag in winners):
        return FlagState.OFF
    return resolve_conflict({str(index): flag.state for index, flag in enumerate(winners)})