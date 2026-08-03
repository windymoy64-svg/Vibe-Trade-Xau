"""Market-aware strategy auto-selection services."""

from .market_indicators import (
    MarketIndicatorSnapshot,
    OHLCVBar,
    RealtimeMarketIndicatorService,
)
from .strategy_selector import (
    RiskProtectedStrategySelectionService,
    StrategyCandidateDecision,
    StrategyDefinition,
    StrategySelectionResult,
    StrategySelectionService,
)

__all__ = [
    "MarketIndicatorSnapshot",
    "OHLCVBar",
    "RealtimeMarketIndicatorService",
    "RiskProtectedStrategySelectionService",
    "StrategyCandidateDecision",
    "StrategyDefinition",
    "StrategySelectionResult",
    "StrategySelectionService",
]
