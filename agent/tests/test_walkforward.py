from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.trading.research import Leaderboard
from src.trading.research.experiment_result import ExperimentResult
from src.trading.walkforward import WalkForwardConfig, WalkForwardEngine, WindowGenerator, WindowType


UTC = timezone.utc


def _metrics(profit_factor, trade_count=10):
    return {
        "win_rate": 0.6,
        "profit_factor": profit_factor,
        "expectancy": 0.5,
        "maximum_drawdown": 100.0,
        "total_trades": trade_count,
        "net_profit": 500.0,
        "recovery_factor": 5.0,
        "average_r": 0.5,
    }


class FakeRunner:
    def __init__(self):
        self.calls = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        return ExperimentResult(
            kwargs["experiment_id"],
            dict(kwargs["parameter_set"]),
            _metrics(1.8),
            kwargs["runtime_version"],
            datetime.now(UTC),
        )


class FakeExperiment:
    def __init__(self):
        self.config = SimpleNamespace(strategy_name="production-replay", runtime_version="production-replay-v1")
        self.runner = FakeRunner()
        self.leaderboard = Leaderboard()
        self.research_calls = []

    def run(self, csv_path, output_dir, **kwargs):
        self.research_calls.append((csv_path, output_dir, kwargs))
        return [
            ExperimentResult("lower", {"RR": 1.5}, _metrics(1.5), "v1", datetime.now(UTC)),
            ExperimentResult("best", {"RR": 2.0}, _metrics(2.0), "v1", datetime.now(UTC)),
        ]


def test_window_generator_modes_and_forward_non_overlap():
    start = datetime(2020, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=12)
    for kind in WindowType:
        config = WalkForwardConfig(
            timedelta(days=3), timedelta(days=1), timedelta(days=2), timedelta(days=2), kind
        )
        windows = WindowGenerator(config).generate(start, end)
        assert len(windows) >= 3
        assert all(row.train.end == row.validation.start and row.validation.end == row.forward.start for row in windows)
        assert all(windows[i - 1].forward.end <= windows[i].forward.start for i in range(1, len(windows)))
        if kind is WindowType.EXPANDING:
            assert len({row.train.start for row in windows}) == 1
            assert windows[1].train.end > windows[0].train.end
        else:
            assert windows[1].train.start > windows[0].train.start


def test_overlapping_forward_periods_are_rejected():
    with pytest.raises(ValueError, match="overlapping forward"):
        WalkForwardConfig(timedelta(days=3), timedelta(days=1), timedelta(days=2), timedelta(days=1))


def test_three_windows_reuse_research_runner_and_generate_reports(tmp_path):
    source = tmp_path / "XAUUSD_D1.csv"
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("timestamp", "open", "high", "low", "close", "volume"))
        for day in range(10):
            timestamp = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=day)
            writer.writerow((timestamp.isoformat(), 2000 + day, 2002 + day, 1999 + day, 2001 + day, 100))
    experiment = FakeExperiment()
    config = WalkForwardConfig(
        training_size=timedelta(days=3),
        validation_size=timedelta(days=1),
        forward_size=timedelta(days=1),
        step_size=timedelta(days=1),
        minimum_trades=3,
    )
    output = tmp_path / "reports" / "walkforward"
    result = WalkForwardEngine(config, experiment).run(source, output, symbol="XAUUSD", timeframe="1d")

    assert len(result.windows) == 6
    assert len(experiment.research_calls) == 6
    assert len(experiment.runner.calls) == 12  # validation + forward via the existing StrategyRunner contract
    assert all(row.best_parameter_set == {"RR": 2.0} for row in result.windows)
    assert all(call["parameter_set"] == {"RR": 2.0} for call in experiment.runner.calls)
    assert all(result.windows[i - 1].window.forward.end <= result.windows[i].window.forward.start for i in range(1, 6))
    assert all(result.windows[i - 1].window.index + 1 == result.windows[i].window.index for i in range(1, 6))

    expected = {
        "walkforward_summary.csv", "walkforward_details.csv", "walkforward_summary.txt", "walkforward.json"
    }
    assert expected <= {path.name for path in output.iterdir()}
    payload = json.loads((output / "walkforward.json").read_text(encoding="utf-8"))
    assert len(payload["windows"]) == 6
    assert set(payload["windows"][0]) >= {
        "window_index", "train_period", "validation_period", "forward_period", "best_parameter_set", "forward_metrics"
    }
    assert "Overall Stability\nPASS" in (output / "walkforward_summary.txt").read_text(encoding="utf-8")
    assert result.stability.passed
