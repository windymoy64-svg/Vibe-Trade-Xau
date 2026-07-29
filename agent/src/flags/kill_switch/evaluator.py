"""Fail-closed hierarchical kill evaluation."""
from __future__ import annotations
from collections.abc import Iterable
from src.flags.kill_switch.models import KillRule, KillScope, KillState


def evaluate_kill(rules: Iterable[KillRule], *, broker: str | None = None, operation: str | None = None) -> dict[str, object]:
    applicable = []
    for rule in rules:
        if rule.scope == KillScope.GLOBAL or (rule.scope == KillScope.BROKER and rule.name == broker) or (rule.scope == KillScope.OPERATION and rule.name == operation):
            applicable.append(rule)
    halted = any(rule.state == KillState.HALT for rule in applicable)
    winner = next((rule for rule in applicable if rule.state == KillState.HALT and rule.scope == KillScope.GLOBAL), None)
    winner = winner or next((rule for rule in applicable if rule.state == KillState.HALT and rule.scope == KillScope.BROKER), None)
    winner = winner or next((rule for rule in applicable if rule.state == KillState.HALT), None)
    return {"halted": halted, "state": KillState.HALT.value if halted else KillState.CLEAR.value, "scope": winner.scope.value if winner else None, "reason": winner.reason if winner else "no applicable halt", "evidence_only": True}