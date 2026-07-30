"""Descriptive parameter consistency and observed outcome separation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean
from typing import Any, Iterable

from .parameter_statistics import METRICS, Observation, canonical_value


@dataclass(frozen=True)
class ParameterImportance:
    rank: int
    parameter: str
    influence_score: float
    stable_value: Any
    top_occurrences: int
    top_frequency: float
    stable_value_average_profit_factor: float
    distinct_values: int


def calculate_parameter_importance(observations: Iterable[Observation]) -> tuple[ParameterImportance, ...]:
    rows = tuple(observations)
    names = sorted({key for row in rows for key in row.parameters})
    unranked = []
    for parameter in names:
        relevant = [row for row in rows if parameter in row.parameters]
        top = [row for row in relevant if row.top_ranked]
        values = sorted({canonical_value(row.parameters[parameter]) for row in relevant})
        top_counts = {value: sum(canonical_value(row.parameters[parameter]) == value for row in top) for value in values}
        stable_key = min(values, key=lambda value: (-top_counts[value], value))
        stable_rows = [row for row in relevant if canonical_value(row.parameters[parameter]) == stable_key]
        influence = fmean(_normalized_group_range(relevant, parameter, metric) for metric in METRICS)
        unranked.append(
            (
                parameter,
                influence,
                stable_rows[0].parameters[parameter],
                top_counts[stable_key],
                top_counts[stable_key] / len(top) if top else 0.0,
                fmean(_finite(row.metrics["profit_factor"]) for row in stable_rows),
                len(values),
            )
        )
    unranked.sort(key=lambda row: (-row[1], row[0]))
    return tuple(ParameterImportance(index, *row) for index, row in enumerate(unranked, 1))


def _normalized_group_range(rows: list[Observation], parameter: str, metric: str) -> float:
    keys = sorted({canonical_value(row.parameters[parameter]) for row in rows})
    means = [
        fmean(_finite(row.metrics[metric]) for row in rows if canonical_value(row.parameters[parameter]) == key)
        for key in keys
    ]
    if len(means) < 2:
        return 0.0
    return (max(means) - min(means)) / max(max(abs(value) for value in means), 1e-12)


def _finite(value: float) -> float:
    number = float(value)
    return number if math.isfinite(number) else math.copysign(1e12, number)
