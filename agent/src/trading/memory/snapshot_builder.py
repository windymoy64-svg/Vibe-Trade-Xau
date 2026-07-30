"""Validation-only builders for memory snapshots; contains no trading logic."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from .memory_schema import TradingMemory

ModelT = TypeVar("ModelT", bound=BaseModel)


def build_snapshot(model: type[ModelT], values: ModelT | dict[str, Any]) -> ModelT:
    """Return an existing snapshot or validate a mapping as the requested model."""
    return values if isinstance(values, model) else model.model_validate(values)


def build_memory(values: TradingMemory | dict[str, Any]) -> TradingMemory:
    """Validate and freeze one complete memory."""
    return build_snapshot(TradingMemory, values)
