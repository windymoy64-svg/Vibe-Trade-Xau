"""Deterministic evidence-based detection of recurring loss patterns."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from src.diagnostics.store import DiagnosticsStore
from src.diagnostics.recommendation_service import DiagnosticRecommendationService


@dataclass(frozen=True)
class _PatternRule:
    key: str
    name: str
    category: str
    description: str
    matches: Callable[[dict[str, object]], bool]


_RULES = (
    _PatternRule(
        "counter-trend", "Counter-trend entry", "TREND",
        "Entries execute against the dominant trend or with mixed EMA confirmation.",
        lambda trade: (
            (trade["direction"] == "BUY" and trade["trend_status"] == "BEARISH")
            or (trade["direction"] == "SELL" and trade["trend_status"] == "BULLISH")
            or trade["ema_alignment"] == "MIXED"
        ),
    ),
    _PatternRule(
        "ranging-market", "Ranging market exposure", "REGIME",
        "Signals trigger inside low-directional ranging conditions.",
        lambda trade: trade["market_regime"] == "RANGING",
    ),
    _PatternRule(
        "asia-session", "Asia session weakness", "SESSION",
        "Loss concentration increases during lower-liquidity Asia hours.",
        lambda trade: trade["trading_session"] == "ASIA",
    ),
    _PatternRule(
        "weak-momentum", "Weak entry momentum", "MOMENTUM",
        "Entries lack sufficient volume or decisive RSI momentum.",
        lambda trade: trade["volume_status"] == "LOW"
        or 45 <= float(trade["rsi_value"]) <= 55,
    ),
)


class LossPatternDetectionService:
    """Detect and persist recurring patterns from loss-only trade snapshots."""

    def __init__(self, store: DiagnosticsStore, *, minimum_support: int = 2) -> None:
        if minimum_support < 1:
            raise ValueError("minimum_support must be at least 1")
        self.store = store
        self.minimum_support = minimum_support

    def detect(self, user_id: str, period_start: str, period_end: str) -> list[dict[str, object]]:
        """Analyze and replace one period snapshot, returning detected patterns."""
        if not user_id.strip():
            raise ValueError("user_id must not be empty")
        if period_start > period_end:
            raise ValueError("period_start must not be after period_end")

        losses = self.store.loss_snapshots(user_id, period_start, period_end)
        total_losses = len(losses)
        generated_at = datetime.now(timezone.utc).isoformat()
        patterns: list[dict[str, object]] = []
        for rule in _RULES:
            evidence_ids = [str(trade["id"]) for trade in losses if rule.matches(trade)]
            count = len(evidence_ids)
            if count < self.minimum_support:
                continue
            percentage = round(count / total_losses * 100, 2)
            patterns.append({
                "id": "pattern_" + uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"vibe-trading:{user_id}:{rule.key}:{period_start}:{period_end}",
                ).hex[:16],
                "name": rule.name,
                "category": rule.category,
                "description": rule.description,
                "loss_count": count,
                "loss_percentage": percentage,
                "confidence": round(min(99.0, 50.0 + percentage / 2), 2),
                "severity": "HIGH" if percentage >= 40 else "MEDIUM" if percentage >= 20 else "LOW",
                "evidence_trade_ids": evidence_ids[:100],
                "trend_delta": 0.0,
            })

        patterns.sort(key=lambda item: (-float(item["loss_percentage"]), str(item["name"])))
        self.store.replace_loss_patterns(
            user_id, period_start, period_end, generated_at, patterns,
        )
        DiagnosticRecommendationService(self.store).generate_and_persist(user_id)
        return patterns