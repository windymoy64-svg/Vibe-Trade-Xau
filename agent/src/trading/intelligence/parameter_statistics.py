"""Deterministic descriptive statistics grouped by parameter value."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from statistics import fmean, pvariance
from typing import Any, Iterable


@dataclass(frozen=True)
class Observation:
    source_id: str
    parameters: dict[str, Any]
    metrics: dict[str, float]
    top_ranked: bool = False


@dataclass(frozen=True)
class ParameterValueStatistics:
    parameter: str
    value: Any
    occurrences: int
    average_profit_factor: float
    average_win_rate: float
    average_drawdown: float
    average_expectancy: float
    average_net_profit: float
    best_value: Any
    worst_value: Any
    variance: float


METRICS = ("profit_factor", "win_rate", "maximum_drawdown", "expectancy", "net_profit")


def calculate_parameter_statistics(observations: Iterable[Observation]) -> tuple[ParameterValueStatistics, ...]:
    rows = tuple(observations)
    grouped: dict[str, dict[str, tuple[Any, list[Observation]]]] = {}
    for row in rows:
        for parameter, value in row.parameters.items():
            key = canonical_value(value)
            grouped.setdefault(parameter, {}).setdefault(key, (value, []))[1].append(row)
    output: list[ParameterValueStatistics] = []
    for parameter in sorted(grouped):
        value_groups = grouped[parameter]
        summaries = {
            key: {metric: _mean(item.metrics[metric] for item in group) for metric in METRICS}
            for key, (_, group) in value_groups.items()
        }
        ordered = sorted(
            value_groups,
            key=lambda key: (
                -summaries[key]["profit_factor"],
                -summaries[key]["expectancy"],
                summaries[key]["maximum_drawdown"],
                key,
            ),
        )
        best, worst = value_groups[ordered[0]][0], value_groups[ordered[-1]][0]
        for key in sorted(value_groups):
            value, group = value_groups[key]
            profit_factors = [_finite(item.metrics["profit_factor"]) for item in group]
            output.append(
                ParameterValueStatistics(
                    parameter=parameter,
                    value=value,
                    occurrences=len(group),
                    average_profit_factor=summaries[key]["profit_factor"],
                    average_win_rate=summaries[key]["win_rate"],
                    average_drawdown=summaries[key]["maximum_drawdown"],
                    average_expectancy=summaries[key]["expectancy"],
                    average_net_profit=summaries[key]["net_profit"],
                    best_value=best,
                    worst_value=worst,
                    variance=pvariance(profit_factors) if len(profit_factors) > 1 else 0.0,
                )
            )
    return tuple(output)


def canonical_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _finite(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        return math.copysign(1e12, number)
    return number


def _mean(values) -> float:
    return fmean(_finite(value) for value in values)
