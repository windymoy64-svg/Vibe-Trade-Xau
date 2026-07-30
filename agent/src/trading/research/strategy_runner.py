"""Run one registered strategy against one historical input."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.trading.analytics import AnalyticsEngine

from .experiment_result import ExperimentResult
from .strategy_registry import StrategyRegistry


class StrategyRunner:
    def __init__(self, registry: StrategyRegistry, analytics: AnalyticsEngine | None = None) -> None:
        self.registry = registry
        self.analytics = analytics or AnalyticsEngine()

    def run(
        self,
        *,
        strategy_name: str,
        parameter_set: dict[str, Any],
        csv_path: str | Path,
        experiment_id: str,
        output_dir: str | Path,
        symbol: str = "XAUUSD",
        timeframe: str = "1h",
        runtime_version: str = "production-replay-v1",
    ) -> ExperimentResult:
        runtime = self.registry.create(strategy_name, parameter_set)
        if not hasattr(runtime, "run_csv"):
            raise TypeError("registered runtime must expose run_csv")
        session = runtime.run_csv(csv_path, symbol=symbol, timeframe=timeframe)
        result = self.analytics.analyze(runtime.journal, session, output_dir)
        from datetime import datetime, timezone

        return ExperimentResult(
            experiment_id=experiment_id,
            parameter_set=dict(parameter_set),
            metrics=dict(result.metrics),
            runtime_version=runtime_version,
            timestamp=datetime.now(timezone.utc),
        )
