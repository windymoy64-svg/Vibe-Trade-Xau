"""Deterministic CSV and human-readable experiment intelligence reports."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .correlation_analysis import CorrelationResult
from .parameter_importance import ParameterImportance
from .parameter_statistics import ParameterValueStatistics


class IntelligenceReportGenerator:
    def generate(
        self,
        experiments_analyzed: int,
        statistics: tuple[ParameterValueStatistics, ...],
        importance: tuple[ParameterImportance, ...],
        correlations: tuple[CorrelationResult, ...],
        output_dir: str | Path,
    ) -> dict[str, Path]:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        paths = {
            "parameter_statistics": destination / "parameter_statistics.csv",
            "parameter_importance": destination / "parameter_importance.csv",
            "correlations": destination / "correlations.csv",
            "summary": destination / "experiment_intelligence.txt",
        }
        _write_csv(paths["parameter_statistics"], statistics, list(ParameterValueStatistics.__dataclass_fields__))
        _write_csv(paths["parameter_importance"], importance, list(ParameterImportance.__dataclass_fields__))
        _write_csv(paths["correlations"], correlations, list(CorrelationResult.__dataclass_fields__))
        paths["summary"].write_text(_summary(experiments_analyzed, importance), encoding="utf-8")
        return paths


def _write_csv(path: Path, rows: tuple[object, ...], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _value(value) for key, value in asdict(row).items()})


def _summary(experiments: int, importance: tuple[ParameterImportance, ...]) -> str:
    lines = ["Experiment Intelligence", "", "Experiments analyzed", str(experiments)]
    stable = sorted(importance, key=lambda row: row.parameter)
    for row in stable:
        lines.extend(
            ["", f"Most Stable {row.parameter}", _value(row.stable_value), "", "Average PF", f"{row.stable_value_average_profit_factor:.2f}"]
        )
    if importance:
        lines.extend(
            [
                "", "Parameter with highest influence", importance[0].parameter,
                "", "Weakest parameter", importance[-1].parameter,
            ]
        )
    return "\n".join(str(line) for line in lines) + "\n"


def _value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)
