"""Deterministic AIOS policy decision contracts."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from src.governance.contracts.decisions import DecisionOutcome, GovernanceDecision
from src.aios.policy.context import PolicyContext


def decision_for(context: PolicyContext, outcome: DecisionOutcome, reason_code: str, rationale: str, policy_refs: tuple[str, ...] = ()) -> GovernanceDecision:
    material = "|".join((context.subject_digest, context.action, outcome.value, reason_code, rationale, *policy_refs))
    return GovernanceDecision(decision_id="pd_" + hashlib.sha256(material.encode()).hexdigest()[:32], subject_digest=context.subject_digest, outcome=outcome, decided_at=datetime(1970, 1, 1, tzinfo=timezone.utc), reason_code=reason_code, rationale=rationale, policy_refs=policy_refs)