"""Orchestrates validation and persistence of completed-trade memories."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .memory_schema import TradingMemory
from .memory_writer import MemoryWriter
from .snapshot_builder import build_memory


class MemoryEngine:
    """Schema/writer coordinator only; intentionally contains no trading logic."""

    def __init__(self, writers: Iterable[MemoryWriter] = ()) -> None:
        self.writers = tuple(writers)

    def create(self, values: TradingMemory | dict[str, Any]) -> TradingMemory:
        return build_memory(values)

    def record(self, values: TradingMemory | dict[str, Any]) -> tuple[TradingMemory, tuple[Path, ...]]:
        memory = self.create(values)
        return memory, tuple(writer.write(memory) for writer in self.writers)
