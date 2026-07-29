"""Protocol for pure shadow comparisons."""
from __future__ import annotations
from typing import Mapping, Protocol, Any


class ComparisonPort(Protocol):
    def compare(self, left: Mapping[str, Any], right: Mapping[str, Any]) -> Mapping[str, Any]:
        """Compare evidence and return an observation-only result."""