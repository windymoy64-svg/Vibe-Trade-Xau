"""Zone-anchored stop loss and deterministic multi-target calculation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class TakeProfitLevel:
    label: str
    price: float
    risk_reward: float
    allocation_percentage: float


@dataclass(frozen=True, slots=True)
class TradeLevels:
    direction: Literal["BUY", "SELL"]
    entry_price: float
    stop_loss: float
    risk_distance: float
    targets: tuple[TakeProfitLevel, ...]


class TradeLevelCalculationService:
    def calculate(
        self,
        *,
        direction: Literal["BUY", "SELL"],
        entry_price: float,
        zone_low: float,
        zone_high: float,
        pip_size: float,
        stop_buffer_pips: float = 3.0,
        target_ratios: tuple[float, ...] = (1.0, 2.0, 3.0),
        allocations: tuple[float, ...] = (30.0, 40.0, 30.0),
        liquidity_target: float | None = None,
    ) -> TradeLevels:
        values = (entry_price, zone_low, zone_high, pip_size, stop_buffer_pips, *target_ratios, *allocations)
        if liquidity_target is not None:
            values += (liquidity_target,)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("trade level inputs must be finite")
        if zone_low >= zone_high or entry_price <= 0 or pip_size <= 0 or stop_buffer_pips < 0:
            raise ValueError("invalid entry, zone, or stop buffer")
        if not target_ratios or len(target_ratios) != len(allocations):
            raise ValueError("each target ratio requires an allocation")
        if any(ratio <= 0 for ratio in target_ratios) or any(allocation <= 0 for allocation in allocations):
            raise ValueError("target ratios and allocations must be positive")
        if not math.isclose(sum(allocations), 100.0, abs_tol=1e-9):
            raise ValueError("target allocations must total 100%")
        buffer = pip_size * stop_buffer_pips
        stop_loss = zone_low - buffer if direction == "BUY" else zone_high + buffer
        risk = entry_price - stop_loss if direction == "BUY" else stop_loss - entry_price
        if risk <= 0:
            raise ValueError("entry must be on the profitable side of stop loss")
        if liquidity_target is not None:
            valid_liquidity = liquidity_target > entry_price if direction == "BUY" else liquidity_target < entry_price
            liquidity_risk = (liquidity_target - entry_price) if direction == "BUY" else (entry_price - liquidity_target)
            if valid_liquidity and liquidity_risk >= risk:
                remaining = tuple(zip(target_ratios[1:], allocations[1:]))
                targets = (
                    TakeProfitLevel("TP1 liquidity", round(liquidity_target, 8), round(liquidity_risk / risk, 4), allocations[0]),
                    *tuple(
                        TakeProfitLevel(
                            f"TP{index}",
                            round(entry_price + (risk * ratio) if direction == "BUY" else entry_price - (risk * ratio), 8),
                            ratio,
                            allocation,
                        )
                        for index, (ratio, allocation) in enumerate(remaining, start=2)
                    ),
                )
            else:
                targets = ()
        else:
            targets = ()
        targets = targets or tuple(
            TakeProfitLevel(
                f"TP{index}",
                round(entry_price + (risk * ratio) if direction == "BUY" else entry_price - (risk * ratio), 8),
                ratio,
                allocation,
            )
            for index, (ratio, allocation) in enumerate(zip(target_ratios, allocations), start=1)
        )
        return TradeLevels(
            direction, round(entry_price, 8), round(stop_loss, 8), round(risk, 8), targets,
        )
