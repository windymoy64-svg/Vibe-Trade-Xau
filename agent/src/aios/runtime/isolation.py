"""Research isolation profile declarations without provisioning behavior."""
from __future__ import annotations
from enum import Enum
from pydantic import model_validator
from src.aios.contracts.environment import ExecutionEnvironment
from src.aios.contracts.identifiers import FrozenContract


class NetworkIsolation(str, Enum):
    NONE = "none"
    DECLARED_ONLY = "declared_only"
    OFFLINE = "offline"


class IsolationProfile(FrozenContract):
    name: str
    environment: ExecutionEnvironment = ExecutionEnvironment.RESEARCH
    network: NetworkIsolation = NetworkIsolation.DECLARED_ONLY
    filesystem_read_only: bool = True
    process_isolation: bool = False
    enforced: bool = False

    @model_validator(mode="after")
    def _research_observation(self) -> "IsolationProfile":
        if self.environment != ExecutionEnvironment.RESEARCH or self.enforced:
            raise ValueError("Phase 5 isolation profiles are research-only and unenforced")
        return self