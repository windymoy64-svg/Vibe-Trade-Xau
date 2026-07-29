"""Execution environment and release-channel primitives."""

from enum import Enum


class ExecutionEnvironment(str, Enum):
    RESEARCH = "research"
    PAPER = "paper"
    DEMO = "demo"
    LIVE = "live"


class ReleaseChannel(str, Enum):
    RESEARCH = "research"
    INTERNAL = "internal"
    PAPER = "paper"
    DEMO = "demo"
    LIVE_CANARY = "live-canary"
    LIVE_STABLE = "live-stable"
    EMERGENCY_HOTFIX = "emergency-hotfix"
