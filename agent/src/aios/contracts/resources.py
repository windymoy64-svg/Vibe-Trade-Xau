"""Immutable resource budgets for bounded execution."""

from pydantic import Field

from src.aios.contracts.identifiers import FrozenContract


class ResourceBudget(FrozenContract):
    """Portable execution ceilings; omitted limits remain explicitly unbounded."""

    timeout_seconds: float = Field(gt=0)
    max_memory_mb: int | None = Field(default=None, gt=0)
    max_cpu_seconds: float | None = Field(default=None, gt=0)
    max_concurrency: int = Field(default=1, gt=0)
    max_input_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    max_cost_usd: float | None = Field(default=None, ge=0)
