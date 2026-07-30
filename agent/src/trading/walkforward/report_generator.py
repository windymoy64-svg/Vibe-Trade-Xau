"""CSV, text, and strict JSON walk-forward reports."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .walkforward_result import StabilityMetrics, WindowResult


class WalkForwardReportGenerator:
    def generate(
        self, windows: tuple[WindowResult, ...], stability: StabilityMetrics, output_dir: str | Path
    ) -> dict[str, Path]:
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        paths = {
            "summary_csv": destination / "walkforward_summary.csv",
            "details_csv": destination / "walkforward_details.csv",
            "summary_txt": destination / "walkforward_summary.txt",
            "json": destination / "walkforward.json",
        }
        self._summary_csv(paths["summary_csv"], windows, stability)
        self._details_csv(paths["details_csv"], windows)
        paths["summary_txt"].write_text(self._summary_text(windows, stability), encoding="utf-8")
        payload = {
            "windows": [_window_dict(row) for row in windows],
            "stability": asdict(stability),
            "overall_stability": "PASS" if stability.passed else "FAIL",
        }
        paths["json"].write_text(json.dumps(_strict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return paths

    @staticmethod
    def _summary_csv(path: Path, windows: tuple[WindowResult, ...], stability: StabilityMetrics) -> None:
        fields = [
            "windows", "average_train_profit_factor", "average_forward_profit_factor", "profit_factor_drift",
            "win_rate_drift", "expectancy_drift", "drawdown_drift", "trade_count_drift", "parameter_stability",
            "performance_degradation", "forward_success_ratio", "overall_stability_score", "stable_windows", "status",
        ]
        row = {
            "windows": len(windows),
            "average_train_profit_factor": _average(row.train.profit_factor for row in windows),
            "average_forward_profit_factor": _average(row.forward.profit_factor for row in windows),
            **asdict(stability),
            "status": "PASS" if stability.passed else "FAIL",
        }
        row.pop("passed")
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerow(_strict(row))

    @staticmethod
    def _details_csv(path: Path, windows: tuple[WindowResult, ...]) -> None:
        periods = ["train", "validation", "forward"]
        metrics = ["win_rate", "profit_factor", "expectancy", "maximum_drawdown", "trade_count", "net_profit", "recovery_factor", "average_r"]
        fields = ["window_index", "train_period", "validation_period", "forward_period", "best_parameter_set"]
        fields += [f"{period}_{metric}" for period in periods for metric in metrics]
        fields += ["meets_minimum_trades", "forward_success"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in windows:
                data = {
                    "window_index": row.window.index,
                    "train_period": _period(row.window.train.start, row.window.train.end),
                    "validation_period": _period(row.window.validation.start, row.window.validation.end),
                    "forward_period": _period(row.window.forward.start, row.window.forward.end),
                    "best_parameter_set": json.dumps(row.best_parameter_set, sort_keys=True, separators=(",", ":")),
                    "meets_minimum_trades": row.meets_minimum_trades,
                    "forward_success": row.forward_success,
                }
                for period in periods:
                    data.update({f"{period}_{key}": value for key, value in asdict(getattr(row, period)).items()})
                writer.writerow(_strict(data))

    @staticmethod
    def _summary_text(windows: tuple[WindowResult, ...], stability: StabilityMetrics) -> str:
        return (
            "Walk Forward Validation\n\n"
            f"Windows\n{len(windows)}\n\n"
            f"Average Train PF\n{_average(row.train.profit_factor for row in windows):.2f}\n\n"
            f"Average Forward PF\n{_average(row.forward.profit_factor for row in windows):.2f}\n\n"
            f"PF Drift\n{stability.profit_factor_drift:.1%}\n\n"
            f"Average Win Rate Drift\n{stability.win_rate_drift:.1%}\n\n"
            f"Average Drawdown Drift\n{stability.drawdown_drift:.1%}\n\n"
            f"Stable Windows\n{stability.stable_windows} / {len(windows)}\n\n"
            f"Overall Stability\n{'PASS' if stability.passed else 'FAIL'}\n"
        )


def _window_dict(row: WindowResult) -> dict[str, Any]:
    return {
        "window_index": row.window.index,
        "train_period": {"start": row.window.train.start, "end": row.window.train.end},
        "validation_period": {"start": row.window.validation.start, "end": row.window.validation.end},
        "forward_period": {"start": row.window.forward.start, "end": row.window.forward.end},
        "best_parameter_set": row.best_parameter_set,
        "train_metrics": asdict(row.train),
        "validation_metrics": asdict(row.validation),
        "forward_metrics": asdict(row.forward),
        "meets_minimum_trades": row.meets_minimum_trades,
        "forward_success": row.forward_success,
    }


def _period(start: datetime, end: datetime) -> str:
    # Reports present the inclusive endpoint while computation remains half-open.
    return f"{start.isoformat()} / {(end - timedelta(microseconds=1)).isoformat()}"


def _average(values) -> float:
    rows = tuple(values)
    return sum(rows) / len(rows)


def _strict(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _strict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_strict(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity"
    return value
