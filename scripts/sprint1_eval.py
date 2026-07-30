"""Sprint 1 evaluation: Replay -> Analytics -> Research -> Walk-Forward."""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from src.trading.analytics import AnalyticsEngine
from src.trading.replay.replay_engine import ReplayEngine
from src.trading.research import Experiment, ExperimentConfig, ParameterSpace, StrategyRunner, production_registry
from src.trading.runtime_config import RuntimeConfig
from src.trading.walkforward import WalkForwardConfig, WalkForwardEngine, WindowType

EVAL_RISK = 1.0
PARAMS = {"RR": [2.0], "STOP_DISTANCE": [8.0], "RISK_PERCENT": [EVAL_RISK]}
DATA = ROOT / ".cache" / "optimization" / "XAUUSD_H1_sprint1.csv"


def runtime() -> RuntimeConfig:
    return RuntimeConfig(RISK_PERCENT=EVAL_RISK, STOP_DISTANCE=8.0, RR=2.0)


def replay_metrics(label_dir: Path) -> dict:
    engine = ReplayEngine(progress_interval=0, runtime_config=runtime())
    session = engine.run_csv(DATA, symbol="XAUUSD", timeframe="1h")
    result = AnalyticsEngine().analyze(engine.journal, session, label_dir / "replay")
    keys = ("total_trades", "win_rate", "profit_factor", "expectancy", "maximum_drawdown", "net_profit", "recovery_factor", "average_r")
    return {key: result.metrics[key] for key in keys}


def research_metrics(label_dir: Path) -> dict:
    experiment = Experiment(ExperimentConfig("sprint1"), ParameterSpace(PARAMS), StrategyRunner(production_registry()))
    results = experiment.run(DATA, label_dir / "research", symbol="XAUUSD", timeframe="1h")
    best = max(results, key=lambda row: (row.metrics["profit_factor"], row.metrics["expectancy"], -row.metrics["maximum_drawdown"]))
    keys = ("total_trades", "win_rate", "profit_factor", "expectancy", "maximum_drawdown", "net_profit")
    return {"parameter_set": best.parameter_set, "metrics": {key: best.metrics[key] for key in keys}}


def walkforward_metrics(label_dir: Path) -> dict:
    experiment = Experiment(ExperimentConfig("sprint1-wf"), ParameterSpace(PARAMS), StrategyRunner(production_registry()))
    config = WalkForwardConfig(
        training_size=timedelta(hours=700),
        validation_size=timedelta(hours=160),
        forward_size=timedelta(hours=160),
        step_size=timedelta(hours=160),
        window_type=WindowType.ROLLING,
        minimum_trades=0,
    )
    result = WalkForwardEngine(config, experiment).run(DATA, label_dir / "walkforward", symbol="XAUUSD", timeframe="1h")
    pf = [row.forward.profit_factor for row in result.windows]
    wr = [row.forward.win_rate for row in result.windows]
    dd = [row.forward.maximum_drawdown for row in result.windows]
    return {
        "windows": len(result.windows),
        "average_forward_profit_factor": sum(pf) / len(pf),
        "average_forward_win_rate": sum(wr) / len(wr),
        "average_forward_drawdown": sum(dd) / len(dd),
        "stable_windows": result.stability.stable_windows,
        "overall_stability_score": result.stability.overall_stability_score,
        "passed": result.stability.passed,
        "forward_success_ratio": result.stability.forward_success_ratio,
    }


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    out = ROOT / "reports" / "optimization" / "sprint1" / label
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": label,
        "dataset": str(DATA),
        "replay": replay_metrics(out),
        "research": research_metrics(out),
        "walkforward": walkforward_metrics(out),
    }
    (out / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
