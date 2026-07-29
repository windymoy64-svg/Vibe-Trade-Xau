"""Default-off local provider with no runtime side effects."""
from __future__ import annotations
from datetime import datetime, timezone
from collections.abc import Iterable
from src.flags.models import FeatureFlag
from src.flags.snapshot import FlagSnapshot


class LocalFlagProvider:
    def __init__(self, flags: Iterable[FeatureFlag] = (), *, snapshot_id: str = "local-default") -> None:
        self._flags = {flag.name: flag for flag in flags}
        self._snapshot_id = snapshot_id

    def snapshot(self) -> FlagSnapshot:
        return FlagSnapshot(snapshot_id=self._snapshot_id, captured_at=datetime.now(timezone.utc), flags=dict(self._flags), source="local")