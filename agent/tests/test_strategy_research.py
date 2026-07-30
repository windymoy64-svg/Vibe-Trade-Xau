from datetime import datetime, timezone

from src.trading.research import Experiment, ExperimentConfig, Leaderboard, ParameterSpace
from src.trading.research.experiment_result import ExperimentResult


def test_parameter_space_is_deterministic():
    space = ParameterSpace({"EMA_FAST": [10, 15], "RSI_FILTER": [True, False]})
    assert list(space) == [
        {"EMA_FAST": 10, "RSI_FILTER": True},
        {"EMA_FAST": 10, "RSI_FILTER": False},
        {"EMA_FAST": 15, "RSI_FILTER": True},
        {"EMA_FAST": 15, "RSI_FILTER": False},
    ]
    assert len(space) == 4


def _result(identifier, factor, expectancy, drawdown):
    return ExperimentResult(
        identifier,
        {"RR": identifier},
        {"profit_factor": factor, "expectancy": expectancy, "maximum_drawdown": drawdown},
        "runtime-v1",
        datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def test_leaderboard_uses_profit_factor_then_expectancy_then_drawdown(tmp_path):
    results = [_result("A", 2, 0.2, 100), _result("B", 2, 0.3, 200), _result("C", 1, 9, 1)]
    leaderboard = Leaderboard()
    ranked = leaderboard.rank(results)
    assert [item.experiment_id for item in ranked] == ["B", "A", "C"]
    path = leaderboard.write_csv(results, tmp_path / "leaderboard.csv")
    assert path.exists() and path.read_text(encoding="utf-8").splitlines()[1].split(",")[1] == "B"


def test_experiment_runs_three_configurations_and_saves_results(tmp_path):

    class FakeRunner:
        def run(self, **kwargs):
            from datetime import datetime, timezone

            return ExperimentResult(
                kwargs["experiment_id"],
                kwargs["parameter_set"],
                {"profit_factor": 1, "expectancy": 0, "maximum_drawdown": 0},
                "v1",
                datetime.now(timezone.utc),
            )

    experiment = Experiment(ExperimentConfig("smoke"), ParameterSpace({"RR": [1.5, 2.0, 2.5]}), FakeRunner())
    results = experiment.run("history.csv", tmp_path)
    assert len(results) == 3
    assert (tmp_path / "leaderboard.csv").exists()
    assert (tmp_path / "experiments" / "smoke-0001" / "experiment_result.json").exists()
