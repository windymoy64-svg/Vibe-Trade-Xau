"""Machine-readable Trading Memory journal writer."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .memory_schema import SCHEMA_VERSION, TradingMemory, TradingMemoryJournal
from .memory_writer import MemoryWriter


class JsonMemoryWriter(MemoryWriter):
    def __init__(self, path: str | Path = "journal.json") -> None:
        self.path = Path(path)

    def _read(self) -> TradingMemoryJournal:
        if not self.path.exists():
            return TradingMemoryJournal()
        with self.path.open("r", encoding="utf-8") as stream:
            return TradingMemoryJournal.model_validate(json.load(stream))

    def write(self, memory: TradingMemory) -> Path:
        journal = self._read()
        if any(item.identity.memory_id == memory.identity.memory_id for item in journal.memories):
            raise ValueError(f"memory_id already exists: {memory.identity.memory_id}")
        updated = TradingMemoryJournal(schema_version=SCHEMA_VERSION, memories=journal.memories + (memory,))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False, suffix=".tmp") as stream:
            stream.write(updated.model_dump_json(indent=2))
            temporary = Path(stream.name)
        os.replace(temporary, self.path)
        return self.path
