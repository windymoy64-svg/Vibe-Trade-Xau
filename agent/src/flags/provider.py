"""Feature-flag provider abstraction."""
from __future__ import annotations
from typing import Protocol
from src.flags.snapshot import FlagSnapshot


class FlagProvider(Protocol):
    def snapshot(self) -> FlagSnapshot: ...