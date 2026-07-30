"""Internally consistent performance statistics for replay trades."""

from __future__ import annotations

import math
from typing import Any, Iterable


def calculate_performance_metrics(trades: Iterable[object], session: object) -> dict[str, Any]:
    rows = list(trades)
    profits = [float(getattr(row, "profit", 0.0)) for row in rows]
    multiples = [float(getattr(row, "r_multiple", 0.0)) for row in rows]
    wins = [value for value in profits if value > 0]
    losses = [value for value in profits if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    total = len(rows)
    maximum_drawdown = _maximum_drawdown(getattr(session, "equity_history", ()))
    if not maximum_drawdown:
        maximum_drawdown = float(getattr(session, "drawdown", 0.0))
    net_profit = sum(profits)
    return {
        "total_trades": total,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "breakeven_trades": total - len(wins) - len(losses),
        "win_rate": len(wins) / total if total else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else (math.inf if gross_profit else 0.0),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_profit": net_profit,
        "average_win": sum(wins) / len(wins) if wins else 0.0,
        "average_loss": sum(losses) / len(losses) if losses else 0.0,
        "average_r": sum(multiples) / total if total else 0.0,
        # Expectancy is expressed in R, matching the requested report example.
        "expectancy": sum(multiples) / total if total else 0.0,
        "average_holding_time": sum(int(getattr(row, "holding_candles", 0)) for row in rows) / total if total else 0.0,
        "longest_win_streak": _longest_streak(profits, positive=True),
        "longest_loss_streak": _longest_streak(profits, positive=False),
        "maximum_drawdown": maximum_drawdown,
        "recovery_factor": net_profit / maximum_drawdown if maximum_drawdown else (math.inf if net_profit > 0 else 0.0),
        "largest_win": max(wins, default=0.0),
        "largest_loss": min(losses, default=0.0),
    }


def _longest_streak(values: list[float], *, positive: bool) -> int:
    longest = current = 0
    for value in values:
        matches = value > 0 if positive else value < 0
        current = current + 1 if matches else 0
        longest = max(longest, current)
    return longest


def _maximum_drawdown(history: Iterable[object]) -> float:
    peak: float | None = None
    maximum = 0.0
    for item in history:
        value = float(item[1] if isinstance(item, (tuple, list)) else getattr(item, "equity"))
        peak = value if peak is None else max(peak, value)
        maximum = max(maximum, peak - value)
    return maximum
