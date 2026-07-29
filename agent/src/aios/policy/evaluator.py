"""Policy evaluator protocol."""
from __future__ import annotations
from typing import Protocol
from src.aios.policy.context import PolicyContext
from src.governance.contracts.decisions import GovernanceDecision


class PolicyEvaluator(Protocol):
    def evaluate(self, context: PolicyContext) -> GovernanceDecision: ...