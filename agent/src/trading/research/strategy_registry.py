"""Explicit parameter-to-runtime factory registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.trading.forex_risk import RiskConfiguration
from src.trading.replay.replay_engine import ReplayEngine
from src.trading.runtime_config import RuntimeConfig

RuntimeFactory = Callable[[dict[str, Any]], object]


class StrategyRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, RuntimeFactory] = {}

    def register(self, name: str, factory: RuntimeFactory) -> None:
        key = name.strip()
        if not key or not callable(factory):
            raise ValueError("strategy name and callable factory are required")
        if key in self._factories:
            raise ValueError(f"strategy {key!r} is already registered")
        self._factories[key] = factory

    def create(self, name: str, parameters: dict[str, Any]) -> object:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise KeyError(f"unknown research strategy: {name!r}") from exc
        return factory(dict(parameters))


def production_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register("production-replay", _production_replay)
    return registry


def _production_replay(parameters: dict[str, Any]) -> ReplayEngine:
    """Build only configurations that the protected ReplayEngine truly exposes."""
    normalized = {key.upper(): value for key, value in parameters.items()}
    initial_balance = float(normalized.pop("INITIAL_BALANCE", 10_000.0))
    runtime = RuntimeConfig.model_validate(normalized)
    defaults = {
        "risk_percent": 0.01,
        "stop_loss_distance": 10.0,
        "reward_ratio": 2.0,
        "max_spread": 1_000.0,
        "min_free_margin": 0.0,
        "min_margin_level": 0.0,
        "max_daily_loss": 1_000_000.0,
        "max_drawdown_percent": 100.0,
        "max_trades_per_day": 100,
        "max_consecutive_losses": 100,
        "max_symbol_exposure": 1_000_000.0,
        "max_correlated_exposure": 1_000_000.0,
        "max_slippage": 20.0,
        "expiration_seconds": 30 * 86_400,
    }
    risk = RiskConfiguration(
        **{
            **defaults,
            "risk_percent": runtime.risk_percent,
            "stop_loss_distance": runtime.stop_distance,
            "reward_ratio": runtime.rr,
        }
    )
    return ReplayEngine(
        initial_balance=initial_balance, risk_configuration=risk, progress_interval=0, runtime_config=runtime
    )
