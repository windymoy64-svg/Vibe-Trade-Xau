"""Strict validation and conservative normalization of trading parameters."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Literal

_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{1,31}$")
_TIMEFRAMES = frozenset({"M1", "M5", "M15", "M30", "H1", "H4", "D1"})


@dataclass(frozen=True, slots=True)
class TradingParameters:
    symbol: str
    timeframe: str
    side: Literal["BUY", "SELL"]
    lot_size: float
    entry_price: float
    stop_loss: float
    take_profit: float


@dataclass(frozen=True, slots=True)
class TradingParameterLimits:
    minimum_lot: float = 0.01
    maximum_lot: float = 1.0
    lot_step: float = 0.01


class TradingParameterValidationService:
    def validate(
        self,
        parameters: TradingParameters,
        limits: TradingParameterLimits = TradingParameterLimits(),
    ) -> TradingParameters:
        symbol = str(parameters.symbol or "").strip().upper()
        timeframe = str(parameters.timeframe or "").strip().upper()
        side = str(parameters.side or "").strip().upper()
        if not _SYMBOL_RE.fullmatch(symbol):
            raise ValueError("symbol contains unsupported characters")
        if timeframe not in _TIMEFRAMES:
            raise ValueError("unsupported trading timeframe")
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")

        values = (
            parameters.lot_size,
            parameters.entry_price,
            parameters.stop_loss,
            parameters.take_profit,
            limits.minimum_lot,
            limits.maximum_lot,
            limits.lot_step,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("trading parameters must be finite")
        if limits.minimum_lot <= 0 or limits.maximum_lot < limits.minimum_lot or limits.lot_step <= 0:
            raise ValueError("invalid broker lot limits")
        if parameters.lot_size < limits.minimum_lot or parameters.lot_size > limits.maximum_lot:
            raise ValueError("lot size is outside broker limits")
        if min(parameters.entry_price, parameters.stop_loss, parameters.take_profit) <= 0:
            raise ValueError("trading prices must be positive")

        lot_size = float(
            (Decimal(str(parameters.lot_size)) / Decimal(str(limits.lot_step))).to_integral_value(
                rounding=ROUND_DOWN,
            ) * Decimal(str(limits.lot_step))
        )
        if lot_size < limits.minimum_lot:
            raise ValueError("normalized lot size is below broker minimum")
        if side == "BUY" and not parameters.stop_loss < parameters.entry_price < parameters.take_profit:
            raise ValueError("BUY requires stop loss < entry < take profit")
        if side == "SELL" and not parameters.take_profit < parameters.entry_price < parameters.stop_loss:
            raise ValueError("SELL requires take profit < entry < stop loss")
        return TradingParameters(
            symbol,
            timeframe,
            side,  # type: ignore[arg-type]
            lot_size,
            parameters.entry_price,
            parameters.stop_loss,
            parameters.take_profit,
        )
