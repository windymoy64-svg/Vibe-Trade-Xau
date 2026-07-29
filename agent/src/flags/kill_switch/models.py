"""Immutable hierarchical kill-switch contracts."""
from __future__ import annotations
from enum import Enum
from src.aios.contracts.identifiers import FrozenContract


class KillScope(str, Enum):
    GLOBAL = "global"
    BROKER = "broker"
    OPERATION = "operation"


class KillState(str, Enum):
    CLEAR = "clear"
    HALT = "halt"


class KillRule(FrozenContract):
    scope: KillScope
    name: str
    state: KillState = KillState.CLEAR
    reason: str = ""