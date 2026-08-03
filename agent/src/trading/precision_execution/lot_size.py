"""Risk-based lot sizing with broker step and boundary enforcement."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True, slots=True)
class LotSizeCalculation:
    balance: float
    risk_percentage: float
    risk_amount: float
    stop_distance: float
    lot_size: float
    actual_risk_amount: float
    bounded_by: str | None


class LotSizeCalculationService:
    def calculate(
        self,
        *,
        balance: float,
        risk_percentage: float,
        entry_price: float,
        stop_loss: float,
        tick_size: float,
        tick_value_per_lot: float,
        minimum_lot: float = 0.01,
        maximum_lot: float = 1.0,
        lot_step: float = 0.01,
    ) -> LotSizeCalculation:
        values = (
            balance, risk_percentage, entry_price, stop_loss, tick_size,
            tick_value_per_lot, minimum_lot, maximum_lot, lot_step,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("lot sizing inputs must be finite")
        if balance <= 0 or not 0 < risk_percentage <= 100:
            raise ValueError("balance and risk percentage must be positive")
        if min(entry_price, stop_loss, tick_size, tick_value_per_lot, minimum_lot, lot_step) <= 0:
            raise ValueError("price, tick, and lot values must be positive")
        if maximum_lot < minimum_lot or entry_price == stop_loss:
            raise ValueError("invalid lot limits or zero stop distance")
        risk_amount = balance * (risk_percentage / 100)
        stop_distance = abs(entry_price - stop_loss)
        loss_per_lot = (stop_distance / tick_size) * tick_value_per_lot
        raw_lot = risk_amount / loss_per_lot
        stepped = float(
            (Decimal(str(raw_lot)) / Decimal(str(lot_step))).to_integral_value(
                rounding=ROUND_DOWN,
            ) * Decimal(str(lot_step))
        )
        bounded_by = None
        if stepped < minimum_lot:
            lot_size = minimum_lot
            bounded_by = "MINIMUM_LOT"
        elif stepped > maximum_lot:
            lot_size = maximum_lot
            bounded_by = "MAXIMUM_LOT"
        else:
            lot_size = stepped
        actual_risk = lot_size * loss_per_lot
        return LotSizeCalculation(
            round(balance, 2), risk_percentage, round(risk_amount, 2),
            round(stop_distance, 8), round(lot_size, 8), round(actual_risk, 2), bounded_by,
        )
