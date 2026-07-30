"""Read-only runtime-event adapters for canonical AIOS evidence."""

from src.aios.runtime_adapter.adapter import CanonicalRuntimeAdapter, RuntimeAdapter
from src.aios.runtime_adapter.contracts import RuntimeEvent
from src.aios.runtime_adapter.registry import AdapterRegistry
from src.aios.runtime_adapter.replay import ReplayAdapter

__all__ = (
    "AdapterRegistry",
    "CanonicalRuntimeAdapter",
    "ReplayAdapter",
    "RuntimeAdapter",
    "RuntimeEvent",
)
