from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone

import pytest

from src.trading.intelligence import ExperimentAnalyzer
from src.trading.research import ExperimentResult
from src.trading.walkforward import (
    PerformanceMetrics,
    Period,
    StabilityMetrics,
    WalkForwardResult,
    WalkForwardWindow,
    WindowResult,
)


UTC = timezone.utc


def _experiment(identifier, ema, rr, pf, win_rate, drawdown, expectancy, net_profit):
    return ExperimentResult(
        identifier,
        {"EMA_FAST": ema, "RR": rr, "ATR_MULTIPLIER": 1.0},
        {
            "profit_factor": pf,
            "win_rate": win_rate,
            "maximum_drawdown": drawdown,
            "expectancy": expectancy,
            "net_profit": net_profit,
        },
        "v1",
        datetime(2026, 1, 1, tzinfo=UTC),
    )


def _walkforward():
    windows = []
    for index, pf in enumerate((2.2, 2.4), 1):
        start = datetime(2026, index, 1, tzinfo=UTC)
        period = Period(start, start + timedelta(days=1))
        metrics = PerformanceMetrics(0.65, pf, 0.6, 80, 12, 600, 7.5, 0.6)
        windows.append(
            WindowResult(
                WalkForwardWindow(index, period, period, period),
                {"EMA_FAST": 15, "RR": 2.5, "ATR_MULTIPLIER": 1.0},
                metrics,
                metrics,
                metrics,
                True,
                True,
            )
        )
    stability = StabilityMetrics(0, 0, 0, 0, 0, 1, 0, 1, 100, 2, True)
    return WalkForwardResult(tuple(windows), stability, {})


def test_analyzer_consumes_completed_records_and_generates_consistent_reports(tmp_path):
    experiments = [
        _experiment("e1", 10, 1.5, 1.0, 0.40, 200, 0.1, 100),
        _experiment("e2", 10, 2.0, 1.2, 0.45, 180, 0.2, 200),
        _experiment("e3", 15, 2.0, 1.8, 0.55, 130, 0.4, 400),
        _experiment("e4", 15, 2.5, 2.0, 0.60, 110, 0.5, 500),
        _experiment("e5", 20, 2.5, 2.6, 0.70, 70, 0.7, 700),
        _experiment("e6", 20, 3.0, 2.8, 0.75, 50, 0.8, 800),
    ]
    output = tmp_path / "reports" / "intelligence"
    analyzer = ExperimentAnalyzer(top_fraction=0.5)
    result = analyzer.analyze(experiments, [_walkforward()], output)

    assert result.experiments_analyzed == 8
    ema_15 = next(row for row in result.parameter_statistics if row.parameter == "EMA_FAST" and row.value == 15)
    assert ema_15.occurrences == 4
    assert ema_15.average_profit_factor == pytest.approx(2.1)
    assert ema_15.best_value == 20 and ema_15.worst_value == 10
    rr = next(row for row in result.parameter_importance if row.parameter == "RR")
    assert rr.stable_value == 2.5 and rr.top_occurrences == 4
    ema_pf = next(
        row for row in result.correlations if row.parameter == "EMA_FAST" and row.metric == "profit_factor"
    )
    assert ema_pf.correlation > 0.9 and ema_pf.strength == "strong"

    expected = {
        "parameter_statistics.csv",
        "parameter_importance.csv",
        "correlations.csv",
        "experiment_intelligence.txt",
    }
    assert expected == {path.name for path in output.iterdir()}
    with (output / "parameter_statistics.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert sum(int(row["occurrences"]) for row in rows if row["parameter"] == "EMA_FAST") == 8
    summary = (output / "experiment_intelligence.txt").read_text(encoding="utf-8")
    assert "Experiments analyzed\n8" in summary
    assert "Most Stable RR\n2.5" in summary

    # The read-only analyzer cannot run a strategy, replay, optimization, or runtime.
    assert not any(hasattr(analyzer, name) for name in ("run", "replay", "optimize", "fit"))


def test_analyzer_fails_closed_for_empty_or_incomplete_records(tmp_path):
    with pytest.raises(ValueError, match="at least one completed"):
        ExperimentAnalyzer().analyze(output_dir=tmp_path)
    incomplete = ExperimentResult(
        "bad", {"RR": 2}, {"profit_factor": 1}, "v1", datetime(2026, 1, 1, tzinfo=UTC)
    )
    with pytest.raises(KeyError, match="missing metrics"):
        ExperimentAnalyzer().analyze([incomplete], output_dir=tmp_path)
