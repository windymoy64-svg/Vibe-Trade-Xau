"""Mechanical support and resistance zones from confirmed market swings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.trading.auto_selection import OHLCVBar
from .market_structure import MarketStructureMap


@dataclass(frozen=True, slots=True)
class SupportResistanceZone:
    id: str
    type: Literal["SUPPORT", "RESISTANCE"]
    low: float
    high: float
    formed_at: str
    status: Literal["ACTIVE", "INVALID"]
    touches: int


class SupportResistanceDetectionService:
    def __init__(self, *, tolerance_ratio: float = 0.0015, max_zones: int = 8) -> None:
        if tolerance_ratio <= 0 or max_zones <= 0:
            raise ValueError("support/resistance parameters must be positive")
        self.tolerance_ratio = tolerance_ratio
        self.max_zones = max_zones

    def detect(
        self,
        bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
        structure: MarketStructureMap,
    ) -> tuple[SupportResistanceZone, ...]:
        zones: list[SupportResistanceZone] = []
        for swing in structure.swings:
            price = swing.price
            tolerance = max(price * self.tolerance_ratio, 1e-8)
            related = [
                bar for bar in bars[swing.index + 1:]
                if bar.low <= price + tolerance and bar.high >= price - tolerance
            ]
            zone_type: Literal["SUPPORT", "RESISTANCE"] = "SUPPORT" if swing.kind == "LOW" else "RESISTANCE"
            low, high = price - tolerance, price + tolerance
            invalid = any(
                (bar.close < low if zone_type == "SUPPORT" else bar.close > high)
                for bar in bars[swing.index + 1:]
            )
            zones.append(SupportResistanceZone(
                id=f"{zone_type.lower()}-{swing.timestamp}",
                type=zone_type,
                low=round(low, 8),
                high=round(high, 8),
                formed_at=swing.timestamp,
                status="INVALID" if invalid else "ACTIVE",
                touches=len(related),
            ))
        return tuple(_cluster_zones(zones, self.max_zones))


def _cluster_zones(
    zones: list[SupportResistanceZone],
    max_zones: int,
) -> list[SupportResistanceZone]:
    """Merge nearby levels so one swing family becomes one entry area."""
    clusters: list[list[SupportResistanceZone]] = []
    for zone in sorted(zones, key=lambda item: item.low):
        cluster = next(
            (
                group for group in clusters
                if group[0].type == zone.type
                and zone.low <= max(item.high for item in group)
                and zone.high >= min(item.low for item in group)
            ),
            None,
        )
        if cluster is None:
            clusters.append([zone])
        else:
            cluster.append(zone)
    merged: list[SupportResistanceZone] = []
    for group in clusters:
        first = min(group, key=lambda item: item.formed_at)
        low = min(item.low for item in group)
        high = max(item.high for item in group)
        touches = sum(item.touches for item in group)
        status: Literal["ACTIVE", "INVALID"] = "ACTIVE" if any(item.status == "ACTIVE" for item in group) else "INVALID"
        merged.append(SupportResistanceZone(
            id=f"{first.type.lower()}-cluster-{first.formed_at}",
            type=first.type,
            low=round(low, 8),
            high=round(high, 8),
            formed_at=first.formed_at,
            status=status,
            touches=touches,
        ))
    return sorted(merged, key=lambda item: (-item.touches, item.low))[:max_zones]
