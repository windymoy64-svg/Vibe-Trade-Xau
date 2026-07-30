"""Descriptive parameter-to-performance correlations; no model fitting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean
from typing import Iterable

from .parameter_statistics import METRICS, Observation


@dataclass(frozen=True)
class CorrelationResult:
    parameter: str
    metric: str
    correlation: float
    sample_size: int
    strength: str


def calculate_correlations(observations: Iterable[Observation]) -> tuple[CorrelationResult, ...]:
    rows = tuple(observations)
    parameters = sorted({key for row in rows for key in row.parameters})
    output: list[CorrelationResult] = []
    for parameter in parameters:
        numeric = [row for row in rows if parameter in row.parameters and _numeric(row.parameters[parameter]) is not None]
        if len(numeric) < 2 or len({float(row.parameters[parameter]) for row in numeric}) < 2:
            continue
        x = [float(row.parameters[parameter]) for row in numeric]
        for metric in METRICS:
            y = [_finite(row.metrics[metric]) for row in numeric]
            value = _pearson(x, y)
            output.append(CorrelationResult(parameter, metric, value, len(numeric), _strength(value)))
    return tuple(output)


def _numeric(value: object) -> float | None:
    if isinstance(value, (bool, int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    return None


def _finite(value: float) -> float:
    number = float(value)
    return number if math.isfinite(number) else math.copysign(1e12, number)


def _pearson(x: list[float], y: list[float]) -> float:
    mean_x, mean_y = fmean(x), fmean(y)
    numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True))
    denominator = math.sqrt(sum((a - mean_x) ** 2 for a in x) * sum((b - mean_y) ** 2 for b in y))
    return numerator / denominator if denominator else 0.0


def _strength(value: float) -> str:
    magnitude = abs(value)
    if magnitude >= 0.7:
        return "strong"
    if magnitude >= 0.4:
        return "moderate"
    if magnitude >= 0.2:
        return "weak"
    return "negligible"
