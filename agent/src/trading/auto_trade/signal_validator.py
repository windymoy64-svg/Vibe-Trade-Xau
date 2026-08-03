"""Validate trade signals against persisted diagnostic loss evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

Direction = Literal["BUY", "SELL"]
Trend = Literal["BULLISH", "BEARISH", "NEUTRAL", "UNKNOWN"]


class DiagnosticPatternSource(Protocol):
    def loss_pattern_analysis(self, user_id: str) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class SignalValidationContext:
    user_id: str
    direction: Direction
    trend: Trend
    market_regime: str
    session: str
    rsi: float | None

    def __post_init__(self) -> None:
        if not self.user_id.strip():
            raise ValueError("user_id is required")
        if self.rsi is not None and not 0 <= self.rsi <= 100:
            raise ValueError("RSI must be within 0..100")


@dataclass(frozen=True, slots=True)
class SignalValidationResult:
    accepted: bool
    reasons: tuple[str, ...]
    evidence_pattern_ids: tuple[str, ...]


class DiagnosticSignalValidationService:
    """Apply only high-confidence loss-pattern guardrails to a signal."""

    def __init__(self, source: DiagnosticPatternSource, *, minimum_confidence: float = 75.0) -> None:
        if not 0 <= minimum_confidence <= 100:
            raise ValueError("minimum confidence must be within 0..100")
        self._source = source
        self.minimum_confidence = minimum_confidence

    def validate(self, context: SignalValidationContext) -> SignalValidationResult:
        analysis = self._source.loss_pattern_analysis(context.user_id)
        patterns = analysis.get("patterns", [])
        blockers: list[str] = []
        evidence_ids: list[str] = []
        for pattern in patterns if isinstance(patterns, list) else []:
            if not isinstance(pattern, dict):
                continue
            if pattern.get("severity") != "HIGH":
                continue
            try:
                confidence = float(pattern.get("confidence", 0))
            except (TypeError, ValueError):
                continue
            if confidence < self.minimum_confidence:
                continue
            reason = _pattern_blocker(str(pattern.get("category", "")), context)
            if reason is None:
                continue
            pattern_id = str(pattern.get("id", "")).strip()
            blockers.append(reason)
            if pattern_id and pattern_id not in evidence_ids:
                evidence_ids.append(pattern_id)

        if blockers:
            return SignalValidationResult(False, tuple(dict.fromkeys(blockers)), tuple(evidence_ids))
        return SignalValidationResult(
            True,
            ("Signal passed all active high-confidence diagnostic guardrails.",),
            (),
        )


def _pattern_blocker(category: str, context: SignalValidationContext) -> str | None:
    normalized = category.strip().upper()
    if normalized == "TREND":
        aligned = (
            (context.direction == "BUY" and context.trend == "BULLISH")
            or (context.direction == "SELL" and context.trend == "BEARISH")
        )
        if not aligned:
            return f"{context.direction} signal conflicts with {context.trend} trend evidence."
    elif normalized == "REGIME" and context.market_regime.strip().upper() in {
        "RANGING", "TRANSITION", "UNKNOWN",
    }:
        return f"Market regime {context.market_regime.strip().upper()} is blocked by diagnostic evidence."
    elif normalized == "SESSION" and context.session.strip().upper() == "ASIA":
        return "Asia-session entries are blocked by diagnostic evidence."
    elif normalized == "MOMENTUM" and context.rsi is not None:
        if context.direction == "BUY" and context.rsi > 70:
            return f"BUY momentum is overextended at RSI {context.rsi:.2f}."
        if context.direction == "SELL" and context.rsi < 30:
            return f"SELL momentum is overextended at RSI {context.rsi:.2f}."
    return None
