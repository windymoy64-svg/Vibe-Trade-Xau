"""Resource accounting contracts; no limits are enforced."""
from __future__ import annotations
from pydantic import Field
from src.aios.contracts.identifiers import FrozenContract
from src.aios.contracts.resources import ResourceBudget


class ResourceUsage(FrozenContract):
    elapsed_seconds: float = Field(default=0, ge=0)
    cpu_seconds: float = Field(default=0, ge=0)
    peak_memory_mb: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0)


class ResourceAccounting(FrozenContract):
    budget: ResourceBudget
    usage: ResourceUsage
    exceeded_dimensions: tuple[str, ...] = ()
    enforced: bool = False


def account_resources(budget: ResourceBudget, usage: ResourceUsage) -> ResourceAccounting:
    exceeded = []
    checks = (("timeout_seconds", usage.elapsed_seconds, budget.timeout_seconds), ("max_cpu_seconds", usage.cpu_seconds, budget.max_cpu_seconds), ("max_memory_mb", usage.peak_memory_mb, budget.max_memory_mb), ("max_input_tokens", usage.input_tokens, budget.max_input_tokens), ("max_output_tokens", usage.output_tokens, budget.max_output_tokens), ("max_cost_usd", usage.cost_usd, budget.max_cost_usd))
    for name, actual, limit in checks:
        if limit is not None and actual > limit:
            exceeded.append(name)
    return ResourceAccounting(budget=budget, usage=usage, exceeded_dimensions=tuple(exceeded), enforced=False)