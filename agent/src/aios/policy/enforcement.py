"""Observe-only enforcement adapter; it cannot permit or execute actions."""
from __future__ import annotations
from src.aios.policy.context import PolicyContext
from src.governance.contracts.decisions import DecisionOutcome, GovernanceDecision


def observe_recommendation(decision: GovernanceDecision, legacy_allowed: bool) -> GovernanceDecision:
    if not legacy_allowed and decision.outcome == DecisionOutcome.PERMIT:
        return decision.model_copy(update={"outcome": DecisionOutcome.DENY, "reason_code": "legacy-deny-preserved", "rationale": "AIOS recommendation constrained by legacy authority."})
    return decision


def no_execution(_context: PolicyContext, _decision: GovernanceDecision) -> None:
    """Explicitly discard execution: governance observation has no enforcement path."""