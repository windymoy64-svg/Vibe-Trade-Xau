"""Writer contract for Trading Memory persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .memory_schema import TradingMemory


class MemoryWriter(ABC):
    @abstractmethod
    def write(self, memory: TradingMemory) -> Path:
        """Persist one memory and return the destination path."""
