"""Directional price-range overlap between active FVG and ACR zones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .acr_zones import ACRZone
from .fvg import FairValueGap


@dataclass(frozen=True, slots=True)
class FVGACRConfluence:
    fvg_id: str
    acr_zone_id: str
    direction: Literal["BULLISH", "BEARISH"]
    overlap_low: float
    overlap_high: float
    overlap_percentage: float


class FVGACRConfluenceService:
    def detect(
        self,
        gaps: tuple[FairValueGap, ...] | list[FairValueGap],
        zones: tuple[ACRZone, ...] | list[ACRZone],
    ) -> tuple[FVGACRConfluence, ...]:
        confluences: list[FVGACRConfluence] = []
        for gap in gaps:
            if gap.status == "FILLED":
                continue
            for zone in zones:
                if zone.status != "FRESH" or zone.direction != gap.direction:
                    continue
                overlap_low = max(gap.low, zone.low)
                overlap_high = min(gap.high, zone.high)
                if overlap_high <= overlap_low:
                    continue
                smaller_size = min(gap.high - gap.low, zone.high - zone.low)
                percentage = ((overlap_high - overlap_low) / smaller_size) * 100
                confluences.append(FVGACRConfluence(
                    gap.id,
                    zone.id,
                    gap.direction,
                    round(overlap_low, 8),
                    round(overlap_high, 8),
                    round(percentage, 2),
                ))
        return tuple(sorted(
            confluences,
            key=lambda item: (-item.overlap_percentage, item.fvg_id, item.acr_zone_id),
        ))
