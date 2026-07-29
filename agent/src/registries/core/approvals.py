"""Registry approval requirements and evidence references."""

from enum import IntEnum

from pydantic import Field

from src.aios.contracts.identifiers import FrozenContract


class ApprovalTier(IntEnum):
    METADATA = 0
    RESEARCH = 1
    EXTERNAL_ACCESS = 2
    TRADING_RELEVANT = 3
    LIVE_PRIVILEGED = 4


class ApprovalRequirements(FrozenContract):
    """Required role quorum for a registry record."""

    tier: ApprovalTier = ApprovalTier.METADATA
    required_roles: tuple[str, ...] = ()
    minimum_approvals: int = Field(default=0, ge=0)
