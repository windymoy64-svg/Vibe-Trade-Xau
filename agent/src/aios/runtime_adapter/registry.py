"""Process-local registry for read-only runtime adapters."""

from __future__ import annotations

from src.aios.runtime_adapter.adapter import RuntimeAdapter
from src.aios.contracts.identifiers import validate_identifier_segment


class AdapterRegistry:
    """Register adapter objects without persistence, discovery, or runtime control."""

    read_only = True
    execution_authority = "existing-runtime"

    def __init__(self) -> None:
        self._adapters: dict[str, RuntimeAdapter] = {}

    def register(self, adapter: RuntimeAdapter) -> RuntimeAdapter:
        if not isinstance(adapter, RuntimeAdapter):
            raise TypeError("adapter must implement the RuntimeAdapter protocol")
        adapter_id = validate_identifier_segment(adapter.adapter_id, field_name="adapter_id")
        if adapter.read_only is not True:
            raise ValueError("runtime adapters must be read-only")
        if adapter_id in self._adapters:
            raise ValueError(f"runtime adapter already registered: {adapter_id}")
        self._adapters[adapter_id] = adapter
        return adapter

    def get(self, adapter_id: str) -> RuntimeAdapter | None:
        normalized = validate_identifier_segment(adapter_id, field_name="adapter_id")
        return self._adapters.get(normalized)

    def list(self) -> tuple[RuntimeAdapter, ...]:
        return tuple(self._adapters[key] for key in sorted(self._adapters))
