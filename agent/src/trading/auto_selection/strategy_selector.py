"""Deterministic strategy selection from current market conditions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Generic, Literal, TypeVar

from .market_indicators import MarketIndicatorSnapshot, MarketRegime, Trend, Volatility

Recommendation = Literal["SELECTED", "ELIGIBLE", "BLOCKED"]
RiskConfigurationT = TypeVar("RiskConfigurationT")


@dataclass(frozen=True, slots=True)
class StrategyDefinition:
    """Mechanical eligibility rules for one strategy."""

    id: str
    name: str
    description: str
    base_score: int
    regimes: tuple[MarketRegime, ...]
    trends: tuple[Trend, ...]
    volatility: tuple[Volatility, ...]
    rsi_range: tuple[float, float] = (0.0, 100.0)
    minimum_volume_ratio: float = 0.0

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("strategy id and name are required")
        if not 0 <= self.base_score <= 70:
            raise ValueError("base_score must be between 0 and 70")
        if not self.regimes or not self.trends or not self.volatility:
            raise ValueError("strategy condition sets must not be empty")
        if not 0 <= self.rsi_range[0] <= self.rsi_range[1] <= 100:
            raise ValueError("RSI range must be ordered within 0..100")
        if self.minimum_volume_ratio < 0:
            raise ValueError("minimum volume ratio must not be negative")


@dataclass(frozen=True, slots=True)
class StrategyCandidateDecision:
    id: str
    name: str
    description: str
    score: int
    confidence: int
    recommendation: Recommendation
    matched_conditions: tuple[str, ...]
    blocked_by: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StrategySelectionResult:
    symbol: str
    timeframe: str
    market_timestamp: str
    selected_strategy_id: str | None
    reason: str
    candidates: tuple[StrategyCandidateDecision, ...]


DEFAULT_STRATEGIES = (
    StrategyDefinition(
        id="evidence-trend-guard",
        name="Evidence trend guard",
        description="Follow confirmed direction while rejecting non-trending entries.",
        base_score=65,
        regimes=("TRENDING",),
        trends=("BULLISH", "BEARISH"),
        volatility=("NORMAL", "HIGH"),
        rsi_range=(20, 80),
        minimum_volume_ratio=0.8,
    ),
    StrategyDefinition(
        id="acr-retest",
        name="ACR retest continuation",
        description="Wait for a lower-timeframe retest in the dominant direction.",
        base_score=60,
        regimes=("TRENDING", "BREAKOUT"),
        trends=("BULLISH", "BEARISH"),
        volatility=("NORMAL", "HIGH"),
        rsi_range=(25, 75),
        minimum_volume_ratio=0.7,
    ),
    StrategyDefinition(
        id="range-mean-reversion",
        name="Range mean reversion",
        description="Trade rotation around equilibrium in a stable range.",
        base_score=55,
        regimes=("RANGING",),
        trends=("NEUTRAL",),
        volatility=("LOW", "NORMAL"),
        rsi_range=(30, 70),
        minimum_volume_ratio=0.0,
    ),
)


class StrategySelectionService:
    """Rank eligible strategies using only explainable market rules."""

    def __init__(
        self,
        strategies: tuple[StrategyDefinition, ...] = DEFAULT_STRATEGIES,
        *,
        maximum_spread_pips: float | None = None,
        minimum_confidence: int = 75,
    ) -> None:
        if not strategies:
            raise ValueError("at least one strategy is required")
        ids = [strategy.id for strategy in strategies]
        if len(ids) != len(set(ids)):
            raise ValueError("strategy ids must be unique")
        if maximum_spread_pips is not None and maximum_spread_pips <= 0:
            raise ValueError("maximum spread must be positive")
        if not 0 <= minimum_confidence <= 100:
            raise ValueError("minimum confidence must be within 0..100")
        self.strategies = strategies
        self.maximum_spread_pips = maximum_spread_pips
        self.minimum_confidence = minimum_confidence

    def select(
        self,
        snapshot: MarketIndicatorSnapshot,
        *,
        session: str = "UNKNOWN",
        spread_pips: float,
    ) -> StrategySelectionResult:
        """Evaluate, rank, and select one strategy for a market snapshot."""
        if spread_pips < 0:
            raise ValueError("spread must not be negative")
        normalized_session = str(session or "UNKNOWN").strip().upper() or "UNKNOWN"
        global_blocker = None
        if not snapshot.ready:
            global_blocker = "Indicator warmup is incomplete."
        elif (
            self.maximum_spread_pips is not None
            and spread_pips > self.maximum_spread_pips
        ):
            global_blocker = (
                f"Spread {spread_pips:.2f} pips exceeds the "
                f"{self.maximum_spread_pips:.2f}-pip ceiling."
            )

        candidates = [
            self._evaluate(
                strategy,
                snapshot,
                normalized_session,
                spread_pips,
                global_blocker,
            )
            for strategy in self.strategies
        ]
        candidates.sort(key=lambda candidate: (candidate.recommendation == "BLOCKED", -candidate.score, candidate.id))
        selected_index = next(
            (
                index
                for index, candidate in enumerate(candidates)
                if candidate.recommendation == "ELIGIBLE" and candidate.confidence >= self.minimum_confidence
            ),
            None,
        )
        if selected_index is None:
            selected_id = None
            reason = global_blocker or "No strategy passed all market-condition and confidence rules."
        else:
            selected = candidates[selected_index]
            selected_id = selected.id
            candidates[selected_index] = replace(selected, recommendation="SELECTED")
            reason = f"{selected.name} has the highest eligible score ({selected.score})."

        return StrategySelectionResult(
            symbol=snapshot.symbol,
            timeframe=snapshot.timeframe,
            market_timestamp=snapshot.timestamp.isoformat(),
            selected_strategy_id=selected_id,
            reason=reason,
            candidates=tuple(candidates),
        )

    def _evaluate(
        self,
        strategy: StrategyDefinition,
        snapshot: MarketIndicatorSnapshot,
        session: str,
        spread_pips: float,
        global_blocker: str | None,
    ) -> StrategyCandidateDecision:
        matched = [
            f"Session {session}",
            f"Spread {spread_pips:.2f} pips",
        ]
        blockers = [global_blocker] if global_blocker else []
        score = strategy.base_score

        score = _match(snapshot.regime, strategy.regimes, "Market regime", matched, blockers, score, 10)
        score = _match(snapshot.trend, strategy.trends, "Trend", matched, blockers, score, 10)
        score = _match(snapshot.volatility, strategy.volatility, "Volatility", matched, blockers, score, 5)
        if snapshot.rsi is None:
            blockers.append("RSI is unavailable.")
        elif strategy.rsi_range[0] <= snapshot.rsi <= strategy.rsi_range[1]:
            matched.append(f"RSI {snapshot.rsi:.2f} inside {strategy.rsi_range[0]:.0f}-{strategy.rsi_range[1]:.0f}")
            score += 5
        else:
            blockers.append(
                f"RSI {snapshot.rsi:.2f} outside {strategy.rsi_range[0]:.0f}-{strategy.rsi_range[1]:.0f}."
            )
        if snapshot.volume_ratio is None:
            blockers.append("Volume ratio is unavailable.")
        elif snapshot.volume_ratio >= strategy.minimum_volume_ratio:
            matched.append(
                f"Volume ratio {snapshot.volume_ratio:.2f} >= {strategy.minimum_volume_ratio:.2f}"
            )
            score += 5
        else:
            blockers.append(
                f"Volume ratio {snapshot.volume_ratio:.2f} below {strategy.minimum_volume_ratio:.2f}."
            )

        bounded_score = min(100, max(0, score))
        return StrategyCandidateDecision(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            score=bounded_score,
            confidence=bounded_score,
            recommendation="BLOCKED" if blockers else "ELIGIBLE",
            matched_conditions=tuple(matched),
            blocked_by=tuple(blockers),
        )


class RiskProtectedStrategySelectionService(Generic[RiskConfigurationT]):
    """Select strategies without exposing risk configuration to selection logic."""

    def __init__(
        self,
        risk_configuration: RiskConfigurationT,
        selector: StrategySelectionService | None = None,
    ) -> None:
        self._risk_configuration = risk_configuration
        self._selector = selector or StrategySelectionService()

    @property
    def risk_configuration(self) -> RiskConfigurationT:
        return self._risk_configuration

    def select(
        self,
        snapshot: MarketIndicatorSnapshot,
        *,
        session: str = "UNKNOWN",
        spread_pips: float,
    ) -> StrategySelectionResult:
        return self._selector.select(snapshot, session=session, spread_pips=spread_pips)


def _match(
    actual: str,
    allowed: tuple[str, ...],
    label: str,
    matched: list[str],
    blockers: list[str],
    score: int,
    weight: int,
) -> int:
    if actual in allowed:
        matched.append(f"{label} {actual}")
        return score + weight
    blockers.append(f"{label} {actual} is not supported (requires {', '.join(allowed)}).")
    return score
