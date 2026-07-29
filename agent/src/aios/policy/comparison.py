"""Deterministic comparison between legacy and AIOS observations."""
from __future__ import annotations
from typing import Any, Mapping
from src.aios.policy.context import PolicyContext
from src.aios.policy.enforcement import observe_recommendation
from src.governance.contracts.decisions import DecisionOutcome, GovernanceDecision


def compare_decisions(context: PolicyContext, legacy: Mapping[str, Any] | bool, aios: GovernanceDecision) -> dict[str, Any]:
    allowed = legacy if isinstance(legacy, bool) else str(legacy.get("decision", legacy.get("outcome", legacy.get("status", "deny")))).lower() in {"allow", "allowed", "permit", "accepted", "ok", "true"}
    constrained = observe_recommendation(aios, allowed)
    return {"subject_digest": context.subject_digest, "legacy_allowed": allowed, "aios_outcome": constrained.outcome.value, "aios_decision_id": constrained.decision_id, "agreement": (allowed and constrained.outcome == DecisionOutcome.PERMIT) or (not allowed and constrained.outcome != DecisionOutcome.PERMIT), "runtime_authority": "legacy", "evidence_only": True}