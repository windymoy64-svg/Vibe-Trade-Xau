"""Governance actor identities."""

from enum import Enum

from src.aios.contracts.identifiers import FrozenContract, ResourceId


class ActorType(str, Enum):
    HUMAN = "human"
    SERVICE = "service"
    WORKLOAD = "workload"


class Actor(FrozenContract):
    """Authenticated actor reference without authentication implementation."""

    actor_id: ResourceId
    actor_type: ActorType
    roles: tuple[str, ...] = ()
