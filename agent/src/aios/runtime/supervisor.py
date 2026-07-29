"""Observe-only runtime supervisor skeleton with no execution authority."""
from __future__ import annotations
from src.aios.contracts.identifiers import FrozenContract
from src.aios.runtime.context import RuntimeContext
from src.aios.runtime.health import HealthSnapshot
from src.aios.runtime.resources import ResourceAccounting


class SupervisionObservation(FrozenContract):
    context: RuntimeContext
    health: HealthSnapshot
    resources: ResourceAccounting
    executable: bool = False
    authoritative: bool = False
    reason: str = "Phase 5 observation only"


class RuntimeSupervisor:
    def observe(self, context: RuntimeContext, health: HealthSnapshot, resources: ResourceAccounting) -> SupervisionObservation:
        return SupervisionObservation(context=context, health=health, resources=resources)