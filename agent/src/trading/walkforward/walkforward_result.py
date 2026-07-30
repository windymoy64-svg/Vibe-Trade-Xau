"""Immutable walk-forward result contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .window_generator import WalkForwardWindow


@dataclass(frozen=True)
class PerformanceMetrics:
    win_rate: float
    profit_factor: float
    expectancy: float
    maximum_drawdown: float
    trade_count: int
    net_profit: float
    recovery_factor: float
    average_r: float

    @classmethod
    def from_analytics(cls, metrics: dict[str, Any]) -> "PerformanceMetrics":
        return cls(
            win_rate=float(metrics["win_rate"]),
            profit_factor=float(metrics["profit_factor"]),
            expectancy=float(metrics["expectancy"]),
            maximum_drawdown=float(metrics["maximum_drawdown"]),
            trade_count=int(metrics["total_trades"]),
            net_profit=float(metrics["net_profit"]),
            recovery_factor=float(metrics["recovery_factor"]),
            average_r=float(metrics["average_r"]),
        )


@dataclass(frozen=True)
class WindowResult:
    window: WalkForwardWindow
    best_parameter_set: dict[str, Any]
    train: PerformanceMetrics
    validation: PerformanceMetrics
    forward: PerformanceMetrics
    meets_minimum_trades: bool
    forward_success: bool


@dataclass(frozen=True)
class StabilityMetrics:
    profit_factor_drift: float
    win_rate_drift: float
    expectancy_drift: float
    drawdown_drift: float
    trade_count_drift: float
    parameter_stability: float
    performance_degradation: float
    forward_success_ratio: float
    overall_stability_score: float
    stable_windows: int
    passed: bool


@dataclass(frozen=True)
class WalkForwardResult:
    windows: tuple[WindowResult, ...]
    stability: StabilityMetrics
    report_paths: dict[str, str]
