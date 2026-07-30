"""Read-only intelligence over completed research and walk-forward records."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from src.trading.research.experiment_result import ExperimentResult
from src.trading.walkforward.walkforward_result import WalkForwardResult

from .correlation_analysis import CorrelationResult, calculate_correlations
from .parameter_importance import ParameterImportance, calculate_parameter_importance
from .parameter_statistics import METRICS, Observation, ParameterValueStatistics, calculate_parameter_statistics
from .report_generator import IntelligenceReportGenerator


@dataclass(frozen=True)
class ExperimentIntelligenceResult:
    experiments_analyzed: int
    parameter_statistics: tuple[ParameterValueStatistics, ...]
    parameter_importance: tuple[ParameterImportance, ...]
    correlations: tuple[CorrelationResult, ...]
    report_paths: dict[str, str]


class ExperimentAnalyzer:
    def __init__(self, reporter: IntelligenceReportGenerator | None = None, *, top_fraction: float = 0.25) -> None:
        if not 0 < top_fraction <= 1:
            raise ValueError("top_fraction must be greater than zero and at most one")
        self.reporter = reporter or IntelligenceReportGenerator()
        self.top_fraction = top_fraction

    def analyze(
        self,
        experiments: Iterable[ExperimentResult] = (),
        walkforward_results: Iterable[WalkForwardResult] = (),
        output_dir: str | Path = "reports/intelligence",
    ) -> ExperimentIntelligenceResult:
        research = tuple(experiments)
        observations = list(_research_observations(research, self.top_fraction))
        observations.extend(_walkforward_observations(tuple(walkforward_results)))
        if not observations:
            raise ValueError("at least one completed experiment or walk-forward window is required")
        rows = tuple(observations)
        statistics = calculate_parameter_statistics(rows)
        importance = calculate_parameter_importance(rows)
        correlations = calculate_correlations(rows)
        paths = self.reporter.generate(len(rows), statistics, importance, correlations, output_dir)
        return ExperimentIntelligenceResult(
            len(rows), statistics, importance, correlations, {key: str(value) for key, value in paths.items()}
        )


def _research_observations(results: tuple[ExperimentResult, ...], fraction: float) -> tuple[Observation, ...]:
    if not results:
        return ()
    for result in results:
        _validate_metrics(result.metrics, result.experiment_id)
    ranked = sorted(results, key=_research_rank_key)
    top_count = max(1, math.ceil(len(ranked) * fraction))
    top_ids = {id(result) for result in ranked[:top_count]}
    return tuple(
        Observation(result.experiment_id, dict(result.parameter_set), _metrics(result.metrics), id(result) in top_ids)
        for result in results
    )


def _walkforward_observations(results: tuple[WalkForwardResult, ...]) -> tuple[Observation, ...]:
    rows = []
    for result_index, result in enumerate(results, 1):
        for window in result.windows:
            metrics = asdict(window.forward)
            normalized = {
                "profit_factor": metrics["profit_factor"],
                "win_rate": metrics["win_rate"],
                "maximum_drawdown": metrics["maximum_drawdown"],
                "expectancy": metrics["expectancy"],
                "net_profit": metrics["net_profit"],
            }
            _validate_metrics(normalized, f"walkforward-{result_index}-{window.window.index}")
            rows.append(
                Observation(
                    f"walkforward-{result_index}-{window.window.index}",
                    dict(window.best_parameter_set),
                    _metrics(normalized),
                    True,
                )
            )
    return tuple(rows)


def _research_rank_key(result: ExperimentResult) -> tuple[float, float, float, str]:
    metrics = result.metrics
    return (
        -_finite(metrics["profit_factor"]),
        -_finite(metrics["expectancy"]),
        _finite(metrics["maximum_drawdown"]),
        result.experiment_id,
    )


def _validate_metrics(metrics: dict, identifier: str) -> None:
    missing = set(METRICS) - set(metrics)
    if missing:
        raise KeyError(f"completed result {identifier!r} is missing metrics: {sorted(missing)}")


def _metrics(metrics: dict) -> dict[str, float]:
    return {name: _finite(metrics[name]) for name in METRICS}


def _finite(value: object) -> float:
    if value == "Infinity":
        return 1e12
    if value == "-Infinity":
        return -1e12
    number = float(value)
    return number if math.isfinite(number) else math.copysign(1e12, number)
