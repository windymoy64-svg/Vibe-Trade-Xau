"""Protocol for read-only observation providers."""
from __future__ import annotations
from typing import Mapping, Protocol, Any


class ObservationPort(Protocol):
    def observe(self) -> Mapping[str, Any]:
        """Return one observation without changing runtime state."""