"""Deterministic train-to-forward stability diagnostics."""

from __future__ import annotations

import math

from .walkforward_result import StabilityMetrics, WindowResult


def calculate_stability(windows: tuple[WindowResult, ...]) -> StabilityMetrics:
    if not windows:
        raise ValueError("at least one completed window is required")
    pf = _mean(_drift(row.train.profit_factor, row.forward.profit_factor) for row in windows)
    wr = _mean(_drift(row.train.win_rate, row.forward.win_rate) for row in windows)
    ex = _mean(_drift(row.train.expectancy, row.forward.expectancy) for row in windows)
    dd = _mean(_drift(row.train.maximum_drawdown, row.forward.maximum_drawdown) for row in windows)
    tc = _mean(_drift(row.train.trade_count, row.forward.trade_count) for row in windows)
    parameter_stability = _parameter_stability(windows)
    degradation = _mean(
        (
            _down(row.train.profit_factor, row.forward.profit_factor)
            + _down(row.train.win_rate, row.forward.win_rate)
            + _down(row.train.expectancy, row.forward.expectancy)
            + _up(row.train.maximum_drawdown, row.forward.maximum_drawdown)
        )
        / 4
        for row in windows
    )
    success_ratio = sum(row.forward_success for row in windows) / len(windows)
    stable = sum(
        row.meets_minimum_trades
        and _drift(row.train.profit_factor, row.forward.profit_factor) <= 0.25
        and _drift(row.train.win_rate, row.forward.win_rate) <= 0.25
        and _drift(row.train.maximum_drawdown, row.forward.maximum_drawdown) <= 0.25
        for row in windows
    )
    score = 100 * (
        0.25 * (1 - min(pf, 1))
        + 0.15 * (1 - min(wr, 1))
        + 0.15 * (1 - min(ex, 1))
        + 0.10 * (1 - min(dd, 1))
        + 0.10 * (1 - min(tc, 1))
        + 0.10 * parameter_stability
        + 0.15 * success_ratio
    )
    passed = score >= 70 and success_ratio >= 0.6 and stable / len(windows) >= 0.6
    return StabilityMetrics(pf, wr, ex, dd, tc, parameter_stability, degradation, success_ratio, score, stable, passed)


def _finite(value: float) -> float:
    return value if math.isfinite(value) else 1e12


def _drift(train: float, forward: float) -> float:
    train, forward = _finite(float(train)), _finite(float(forward))
    return abs(forward - train) / max(abs(train), 1e-12)


def _down(train: float, forward: float) -> float:
    train, forward = _finite(float(train)), _finite(float(forward))
    return max(0.0, train - forward) / max(abs(train), 1e-12)


def _up(train: float, forward: float) -> float:
    train, forward = _finite(float(train)), _finite(float(forward))
    return max(0.0, forward - train) / max(abs(train), 1e-12)


def _mean(values) -> float:
    rows = tuple(values)
    return sum(rows) / len(rows)


def _parameter_stability(windows: tuple[WindowResult, ...]) -> float:
    if len(windows) == 1:
        return 1.0
    return sum(windows[i - 1].best_parameter_set == windows[i].best_parameter_set for i in range(1, len(windows))) / (
        len(windows) - 1
    )
