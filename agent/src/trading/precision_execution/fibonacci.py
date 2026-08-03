"""Fibonacci dealing-range premium and discount classification."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class FibonacciValuation:
    swing_low: float
    swing_high: float
    current_price: float
    setup_zone_midpoint: float
    equilibrium: float
    setup_direction: Literal["BUY", "SELL"]
    setup_valuation: Literal["PREMIUM", "DISCOUNT", "EQUILIBRIUM"]
    eligible: bool
    levels: tuple[tuple[str, float], ...]


class FibonacciPremiumDiscountService:
    _RATIOS = (("23.6%", 0.236), ("38.2%", 0.382), ("50.0%", 0.5),
               ("61.8%", 0.618), ("78.6%", 0.786))

    def calculate(
        self,
        *,
        swing_low: float,
        swing_high: float,
        current_price: float,
        setup_zone_midpoint: float,
        setup_direction: Literal["BUY", "SELL"],
    ) -> FibonacciValuation:
        values = (swing_low, swing_high, current_price, setup_zone_midpoint)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Fibonacci inputs must be finite")
        if swing_low >= swing_high:
            raise ValueError("swing low must be below swing high")
        if not swing_low <= setup_zone_midpoint <= swing_high:
            raise ValueError("setup zone midpoint must be inside the dealing range")
        distance = swing_high - swing_low
        equilibrium = swing_low + (distance * 0.5)
        tolerance = distance * 1e-9
        if setup_zone_midpoint < equilibrium - tolerance:
            valuation: Literal["PREMIUM", "DISCOUNT", "EQUILIBRIUM"] = "DISCOUNT"
        elif setup_zone_midpoint > equilibrium + tolerance:
            valuation = "PREMIUM"
        else:
            valuation = "EQUILIBRIUM"
        eligible = valuation == "EQUILIBRIUM" or (
            setup_direction == "BUY" and valuation == "DISCOUNT"
        ) or (setup_direction == "SELL" and valuation == "PREMIUM")
        return FibonacciValuation(
            swing_low, swing_high, current_price, setup_zone_midpoint,
            round(equilibrium, 8), setup_direction, valuation, eligible,
            tuple((label, round(swing_low + (distance * ratio), 8)) for label, ratio in self._RATIOS),
        )
