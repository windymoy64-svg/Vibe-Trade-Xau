"""Monotonic trailing stops anchored to newly confirmed fresh ACR zones."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .acr_zones import ACRZone


@dataclass(frozen=True, slots=True)
class TrailingStopUpdate:
    zone_id: str
    stop_price: float
    formed_at: str


@dataclass(frozen=True, slots=True)
class ACRTrailingStopPlan:
    initial_stop: float
    current_stop: float
    updates: tuple[TrailingStopUpdate, ...]


class ACRTrailingStopService:
    def calculate(
        self,
        *,
        direction: Literal["BUY", "SELL"],
        initial_stop: float,
        current_price: float,
        opened_at: datetime,
        zones: tuple[ACRZone, ...] | list[ACRZone],
        pip_size: float,
        buffer_pips: float = 3.0,
    ) -> ACRTrailingStopPlan:
        if opened_at.tzinfo is None or opened_at.utcoffset() is None:
            raise ValueError("position open time must be timezone-aware")
        if not all(math.isfinite(value) for value in (initial_stop, current_price, pip_size, buffer_pips)):
            raise ValueError("trailing stop inputs must be finite")
        if min(initial_stop, current_price, pip_size) <= 0 or buffer_pips < 0:
            raise ValueError("invalid trailing stop inputs")
        stop = initial_stop
        updates: list[TrailingStopUpdate] = []
        expected_direction = "BULLISH" if direction == "BUY" else "BEARISH"
        eligible = sorted(zones, key=lambda zone: zone.formed_at)
        for zone in eligible:
            formed_at = datetime.fromisoformat(zone.formed_at.replace("Z", "+00:00"))
            if zone.status != "FRESH" or zone.direction != expected_direction or formed_at <= opened_at:
                continue
            candidate = zone.low - (pip_size * buffer_pips) if direction == "BUY" else zone.high + (pip_size * buffer_pips)
            improves = candidate > stop if direction == "BUY" else candidate < stop
            valid_side = candidate < current_price if direction == "BUY" else candidate > current_price
            if not improves or not valid_side:
                continue
            stop = candidate
            updates.append(TrailingStopUpdate(zone.id, round(stop, 8), zone.formed_at))
        return ACRTrailingStopPlan(round(initial_stop, 8), round(stop, 8), tuple(updates))
