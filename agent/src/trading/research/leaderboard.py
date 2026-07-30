"""Deterministic experiment ranking and CSV output."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .experiment_result import ExperimentResult


@dataclass(frozen=True)
class Objective:
    name: str
    descending: bool = True


class Leaderboard:
    DEFAULT_OBJECTIVES = (
        Objective("profit_factor"),
        Objective("expectancy"),
        Objective("maximum_drawdown", descending=False),
    )

    def rank(
        self, results: Iterable[ExperimentResult], objectives: Iterable[Objective] | None = None
    ) -> list[ExperimentResult]:
        ordered = tuple(objectives or self.DEFAULT_OBJECTIVES)
        if not ordered:
            raise ValueError("at least one objective is required")
        for result in results:
            for objective in ordered:
                if objective.name not in result.metrics:
                    raise KeyError(f"metric {objective.name!r} is missing from experiment result")
        ranked = list(results)
        # Stable successive sorts make the first objective the primary key.
        for objective in reversed(ordered):
            ranked.sort(
                key=lambda result: _sort_value(result.metrics[objective.name]),
                reverse=objective.descending,
            )
        return ranked

    def write_csv(
        self, results: Iterable[ExperimentResult], path: str | Path, objectives: Iterable[Objective] | None = None
    ) -> Path:
        ranked = self.rank(results, objectives)
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        parameter_names = sorted({key for result in ranked for key in result.parameter_set})
        metric_names = [
            "win_rate",
            "profit_factor",
            "expectancy",
            "net_profit",
            "maximum_drawdown",
            "recovery_factor",
            "average_r",
            "total_trades",
            "winning_trades",
            "losing_trades",
        ]
        fields = ["rank", "experiment_id", "runtime_version", "timestamp", *parameter_names, *metric_names]
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for index, result in enumerate(ranked, 1):
                writer.writerow(
                    {
                        "rank": index,
                        "experiment_id": result.experiment_id,
                        "runtime_version": result.runtime_version,
                        "timestamp": result.timestamp.isoformat(),
                        **{key: result.parameter_set.get(key, "") for key in parameter_names},
                        **{key: result.metrics.get(key, "") for key in metric_names},
                    }
                )
        return destination


def _sort_value(value: object) -> float:
    if value == "Infinity":
        return float("inf")
    if value == "-Infinity":
        return float("-inf")
    return float(value)
