"""Dynamic selection of realtime entry-area candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .acr_zones import ACRZone
from .fvg import FairValueGap
from .order_blocks import OrderBlock
from .support_resistance import SupportResistanceZone
from .supply_demand import SupplyDemandZone
from .entry_area_confirmation import ReactionStatus, confirm_area_reaction
from src.trading.auto_selection import OHLCVBar
from datetime import datetime

EntryAreaType = Literal[
    "ORDER_BLOCK", "ACR", "FVG", "DEMAND", "SUPPLY", "SUPPORT", "RESISTANCE",
]


@dataclass(frozen=True, slots=True)
class EntryAreaCandidate:
    id: str
    type: EntryAreaType
    direction: Literal["BULLISH", "BEARISH"]
    low: float
    high: float
    score: float
    distance: float
    freshness: float
    confluence_count: int
    reason: str
    reaction_status: ReactionStatus
    age_candles: int
    mitigation_count: int


class DynamicEntryAreaSelector:
    """Score all area types equally from current price and shared evidence."""

    def select(
        self,
        *,
        current_price: float,
        direction: Literal["BULLISH", "BEARISH"],
        order_blocks: tuple[OrderBlock, ...] | list[OrderBlock],
        acr_zones: tuple[ACRZone, ...] | list[ACRZone],
        gaps: tuple[FairValueGap, ...] | list[FairValueGap],
        supply_demand: tuple[SupplyDemandZone, ...] | list[SupplyDemandZone],
        support_resistance: tuple[SupportResistanceZone, ...] | list[SupportResistanceZone],
        bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
        max_distance_ratio: float = 0.02,
        max_mitigations: int = 3,
    ) -> tuple[EntryAreaCandidate, ...]:
        raw: list[tuple[str, EntryAreaType, str, float, float, float, str, int]] = []
        for zone in order_blocks:
            if zone.status in {"FRESH", "PARTIALLY_MITIGATED"} and zone.mitigation_count <= max_mitigations:
                raw.append((zone.id, "ORDER_BLOCK", zone.direction, zone.low, zone.high, 1.0 if zone.status == "FRESH" else 0.65, zone.origin_timestamp, zone.mitigation_count))
        for zone in acr_zones:
            if zone.status == "FRESH":
                raw.append((zone.id, "ACR", zone.direction, zone.low, zone.high, 1.0, zone.formed_at, 0))
        for gap in gaps:
            if gap.status != "FILLED":
                raw.append((gap.id, "FVG", gap.direction, gap.low, gap.high, 1.0 if gap.status == "OPEN" else 0.65, gap.formed_at, 0))
        for zone in supply_demand:
            if zone.status != "INVALID":
                bias = "BULLISH" if zone.type == "DEMAND" else "BEARISH"
                raw.append((zone.id, zone.type, bias, zone.low, zone.high, 1.0 if zone.status == "ACTIVE" else 0.65, zone.formed_at, 1 if zone.status == "TESTED" else 0))
        for zone in support_resistance:
            if zone.status == "ACTIVE":
                bias = "BULLISH" if zone.type == "SUPPORT" else "BEARISH"
                raw.append((zone.id, zone.type, bias, zone.low, zone.high, min(1.0, 0.5 + zone.touches * 0.1), zone.formed_at, zone.touches))

        candidates: list[EntryAreaCandidate] = []
        for item_id, item_type, item_direction, low, high, freshness, formed_at, mitigation_count in raw:
            if item_direction != direction:
                continue
            if low >= high:
                continue
            distance = abs(current_price - ((low + high) / 2))
            scale = max(abs(current_price), 1.0)
            if distance > scale * max_distance_ratio and not (low <= current_price <= high):
                continue
            distance_score = max(0.0, 1.0 - min(distance / (scale * max_distance_ratio), 1.0))
            formed = datetime.fromisoformat(formed_at.replace("Z", "+00:00"))
            age_candles = sum(bar.timestamp > formed for bar in bars)
            reaction_status = confirm_area_reaction(bars, direction=direction, low=low, high=high)
            if reaction_status == "INVALIDATED":
                continue
            overlap_count = sum(
                other_id != item_id and low <= other_high and high >= other_low
                for other_id, _, other_direction, other_low, other_high, _, _, _ in raw
                if other_direction == direction
            )
            reaction_score = {"REACTION_CONFIRMED": 20.0, "TOUCHED": 8.0, "WAITING_RETEST": 0.0}[reaction_status]
            age_penalty = min(age_candles / 100, 1.0) * 10
            mitigation_penalty = min(mitigation_count / max(max_mitigations, 1), 1.0) * 10
            score = round(freshness * 30 + distance_score * 25 + min(overlap_count, 4) * 7.5 + reaction_score - age_penalty - mitigation_penalty, 4)
            candidates.append(EntryAreaCandidate(
                id=item_id,
                type=item_type,
                direction=item_direction,
                low=round(low, 8),
                high=round(high, 8),
                score=score,
                distance=round(distance, 8),
                freshness=round(freshness, 4),
                confluence_count=overlap_count,
                reason=f"{item_type} scored from chart distance, freshness, reaction={reaction_status}, age, mitigation, and {overlap_count} overlap(s).",
                reaction_status=reaction_status,
                age_candles=age_candles,
                mitigation_count=mitigation_count,
            ))
        return tuple(sorted(candidates, key=lambda item: (-item.score, item.distance, item.id)))
