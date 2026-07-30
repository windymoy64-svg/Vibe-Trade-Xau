"""Deterministic multi-configuration experiment orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .experiment_result import ExperimentResult
from .leaderboard import Leaderboard, Objective
from .parameter_space import ParameterSpace
from .strategy_runner import StrategyRunner


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    strategy_name: str = "production-replay"
    runtime_version: str = "production-replay-v1"


class Experiment:
    def __init__(
        self,
        config: ExperimentConfig,
        parameter_space: ParameterSpace,
        runner: StrategyRunner,
        leaderboard: Leaderboard | None = None,
    ) -> None:
        self.config = config
        self.parameter_space = parameter_space
        self.runner = runner
        self.leaderboard = leaderboard or Leaderboard()

    def run(
        self,
        csv_path: str | Path,
        output_dir: str | Path = "reports",
        *,
        symbol: str = "XAUUSD",
        timeframe: str = "1h",
        objectives: list[Objective] | None = None,
    ) -> list[ExperimentResult]:
        if not self.config.name.strip():
            raise ValueError("experiment name must not be empty")
        results: list[ExperimentResult] = []
        for index, parameters in enumerate(self.parameter_space, 1):
            experiment_id = f"{self.config.name}-{index:04d}"
            result_dir = Path(output_dir) / "experiments" / experiment_id
            result = self.runner.run(
                strategy_name=self.config.strategy_name,
                parameter_set=parameters,
                csv_path=csv_path,
                experiment_id=experiment_id,
                output_dir=result_dir,
                symbol=symbol,
                timeframe=timeframe,
                runtime_version=self.config.runtime_version,
            )
            result.save(result_dir / "experiment_result.json")
            results.append(result)
        self.leaderboard.write_csv(results, Path(output_dir) / "leaderboard.csv", objectives)
        return results
