"""Compatibility append-only JSONL audit sink."""
from __future__ import annotations

import json
from pathlib import Path
from src.governance.audit.events import AuditEvent


class JsonlAuditSink:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def append(self, event: AuditEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            handle.flush()

    def read(self) -> tuple[AuditEvent, ...]:
        if not self.path.exists():
            return ()
        return tuple(AuditEvent.model_validate(json.loads(line)) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())