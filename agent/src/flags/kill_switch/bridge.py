"""Non-authoritative bridge to an injected existing HALT mechanism."""
from __future__ import annotations
from typing import Protocol
from src.flags.kill_switch.evaluator import evaluate_kill
from src.flags.kill_switch.models import KillRule


class HaltPort(Protocol):
    def is_halted(self, broker: str | None = None) -> bool: ...


class KillSwitchBridge:
    def __init__(self, halt_port: HaltPort) -> None:
        self._halt_port = halt_port

    def observe(self, rules: tuple[KillRule, ...], *, broker: str | None = None, operation: str | None = None) -> dict[str, object]:
        local = evaluate_kill(rules, broker=broker, operation=operation)
        try:
            authoritative = bool(self._halt_port.is_halted(broker))
            bridge_error = None
        except Exception as exc:
            authoritative = True
            bridge_error = type(exc).__name__
        return {**local, "local_halt": authoritative, "halted": authoritative or bool(local["halted"]), "authority": "existing-halt", "bridge_error": bridge_error, "evidence_only": True}