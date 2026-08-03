"""Fail-closed entry order type recommendation from precision evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class EntryOrderRecommendation:
    recommendation: Literal["BUY LIMIT", "SELL LIMIT", "MARKET BUY", "MARKET SELL", "WAIT"]
    status: Literal["RETEST WAITING", "CONFIRMED", "BLOCKED"]
    current_price: float
    entry_price: float
    distance_points: float
    reasons: tuple[str, ...]


class EntryOrderTypeService:
    def __init__(self, *, market_tolerance_points: float = 0.5) -> None:
        if market_tolerance_points < 0:
            raise ValueError("market tolerance must not be negative")
        self.market_tolerance_points = market_tolerance_points

    def recommend(
        self,
        *,
        direction: Literal["BUY", "SELL"],
        current_price: float,
        entry_price: float,
        zone_fresh: bool,
        valuation_eligible: bool,
        has_confluence: bool,
        reversal_confirmed: bool,
    ) -> EntryOrderRecommendation:
        if not all(math.isfinite(value) and value > 0 for value in (current_price, entry_price)):
            raise ValueError("order prices must be positive and finite")
        blockers = []
        if not zone_fresh:
            blockers.append("ACR zone is not fresh.")
        if not valuation_eligible:
            blockers.append("Fibonacci valuation is not eligible for the direction.")
        if not has_confluence:
            blockers.append("FVG and ACR confluence is unavailable.")
        distance = abs(current_price - entry_price)
        if blockers:
            return EntryOrderRecommendation(
                "WAIT", "BLOCKED", current_price, entry_price, round(distance, 8), tuple(blockers),
            )
        if reversal_confirmed and distance <= self.market_tolerance_points:
            recommendation = "MARKET BUY" if direction == "BUY" else "MARKET SELL"
            return EntryOrderRecommendation(
                recommendation, "CONFIRMED", current_price, entry_price,
                round(distance, 8), ("Reversal confirmed inside market-entry tolerance.",),
            )
        valid_retest = (direction == "BUY" and entry_price < current_price) or (
            direction == "SELL" and entry_price > current_price
        )
        if valid_retest:
            recommendation = "BUY LIMIT" if direction == "BUY" else "SELL LIMIT"
            return EntryOrderRecommendation(
                recommendation, "RETEST WAITING", current_price, entry_price,
                round(distance, 8), ("Wait for price to retest the planned entry.",),
            )
        return EntryOrderRecommendation(
            "WAIT", "BLOCKED", current_price, entry_price, round(distance, 8),
            ("Price has passed the unconfirmed entry level.",),
        )
