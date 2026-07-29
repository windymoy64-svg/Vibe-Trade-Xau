"""Pure local, observe-only policy evaluator."""
from __future__ import annotations
from src.aios.policy.context import PolicyContext
from src.aios.policy.decision import decision_for
from src.governance.contracts.decisions import DecisionOutcome, GovernanceDecision


class LocalPolicyEvaluator:
    def evaluate(self, context: PolicyContext) -> GovernanceDecision:
        try:
            if not context.subject or not context.action:
                raise ValueError("subject and action are required")
            if context.legacy_decision and context.legacy_decision.lower() in {"deny", "denied", "blocked", "false"}:
                return decision_for(context, DecisionOutcome.DENY, "legacy-deny-preserved", "Legacy decision is authoritative.")
            return decision_for(context, DecisionOutcome.NOT_APPLICABLE, "observation-only", "No Phase 3 policy enforcement is configured.")
        except Exception as exc:
            return decision_for(context, DecisionOutcome.ERROR, "evaluation-error", f"Fail-closed observation error: {type(exc).__name__}")