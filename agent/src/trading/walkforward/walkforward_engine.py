"""Research/replay/analytics orchestration for walk-forward validation."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from src.trading.data import HistoricalDataset
from src.trading.research import Experiment, Objective

from .report_generator import WalkForwardReportGenerator
from .stability_metrics import calculate_stability
from .walkforward_result import PerformanceMetrics, WalkForwardResult, WindowResult
from .window_generator import Period, WalkForwardConfig, WindowGenerator


class WalkForwardEngine:
    """Coordinate existing production research components without optimizing itself."""

    def __init__(
        self,
        config: WalkForwardConfig,
        experiment: Experiment,
        *,
        historical_data: HistoricalDataset | None = None,
        reporter: WalkForwardReportGenerator | None = None,
    ) -> None:
        self.config = config
        self.experiment = experiment
        self.historical_data = historical_data or HistoricalDataset()
        self.reporter = reporter or WalkForwardReportGenerator()

    def run(
        self,
        csv_path: str | Path,
        output_dir: str | Path = "reports/walkforward",
        *,
        symbol: str | None = None,
        timeframe: str | None = None,
        objectives: Iterable[Objective] | None = None,
    ) -> WalkForwardResult:
        root = Path(output_dir)
        processed, metadata = self.historical_data.import_file(
            csv_path, symbol=symbol, timeframe=timeframe, output_dir=root / "dataset"
        )
        rows = _read_rows(processed)
        end = _exclusive_end(rows)
        windows = WindowGenerator(self.config).generate(metadata.start, end)
        if not windows:
            raise ValueError("dataset does not contain one complete walk-forward window")
        objective_list = list(objectives) if objectives is not None else None
        completed: list[WindowResult] = []
        for window in windows:
            window_dir = root / "windows" / f"window-{window.index:04d}"
            train_csv = _write_slice(rows, window.train, window_dir / "train.csv")
            validation_csv = _write_slice(rows, window.validation, window_dir / "validation.csv")
            forward_csv = _write_slice(rows, window.forward, window_dir / "forward.csv")
            research_results = self.experiment.run(
                train_csv,
                window_dir / "research",
                symbol=metadata.symbol,
                timeframe=metadata.timeframe,
                objectives=objective_list,
            )
            ranked = self.experiment.leaderboard.rank(research_results, objective_list)
            if not ranked:
                raise RuntimeError(f"research returned no parameter sets for window {window.index}")
            best = ranked[0]
            parameters = dict(best.parameter_set)  # Frozen selection; never mutated after ranking.
            validation = self.experiment.runner.run(
                strategy_name=self.experiment.config.strategy_name,
                parameter_set=parameters,
                csv_path=validation_csv,
                experiment_id=f"walkforward-{window.index:04d}-validation",
                output_dir=window_dir / "validation",
                symbol=metadata.symbol,
                timeframe=metadata.timeframe,
                runtime_version=self.experiment.config.runtime_version,
            )
            forward = self.experiment.runner.run(
                strategy_name=self.experiment.config.strategy_name,
                parameter_set=parameters,
                csv_path=forward_csv,
                experiment_id=f"walkforward-{window.index:04d}-forward",
                output_dir=window_dir / "forward",
                symbol=metadata.symbol,
                timeframe=metadata.timeframe,
                runtime_version=self.experiment.config.runtime_version,
            )
            train_metrics = PerformanceMetrics.from_analytics(best.metrics)
            validation_metrics = PerformanceMetrics.from_analytics(validation.metrics)
            forward_metrics = PerformanceMetrics.from_analytics(forward.metrics)
            enough = forward_metrics.trade_count >= self.config.minimum_trades
            completed.append(
                WindowResult(
                    window,
                    parameters,
                    train_metrics,
                    validation_metrics,
                    forward_metrics,
                    enough,
                    enough and forward_metrics.net_profit > 0 and forward_metrics.profit_factor > 1,
                )
            )
        result_rows = tuple(completed)
        stability = calculate_stability(result_rows)
        paths = self.reporter.generate(result_rows, stability, root)
        return WalkForwardResult(result_rows, stability, {key: str(value) for key, value in paths.items()})


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("historical dataset contains no rows")
    return rows


def _timestamp(row: dict[str, str]) -> datetime:
    parsed = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _exclusive_end(rows: list[dict[str, str]]) -> datetime:
    timestamps = [_timestamp(row) for row in rows]
    interval = timestamps[-1] - timestamps[-2] if len(timestamps) > 1 else timedelta(microseconds=1)
    return timestamps[-1] + max(interval, timedelta(microseconds=1))


def _write_slice(rows: list[dict[str, str]], period: Period, path: Path) -> Path:
    selected = [row for row in rows if period.contains(_timestamp(row))]
    if not selected:
        raise ValueError(f"walk-forward period {period.start.isoformat()} to {period.end.isoformat()} contains no candles")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=("timestamp", "open", "high", "low", "close", "volume"), lineterminator="\n")
        writer.writeheader()
        writer.writerows(selected)
    return path
