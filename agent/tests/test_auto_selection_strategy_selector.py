from dataclasses import FrozenInstanceError, dataclass
from datetime import datetime, timezone

import pytest

from src.trading.auto_selection import (
    MarketIndicatorSnapshot,
    RiskProtectedStrategySelectionService,
    StrategySelectionService,
)


@dataclass(frozen=True)
class FixedRiskConfiguration:
    risk_percent: float
    stop_loss_distance: float
    reward_ratio: float
    max_daily_loss: float


def _snapshot(**overrides) -> MarketIndicatorSnapshot:
    values = {
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "timestamp": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "bar_count": 50,
        "ready": True,
        "close": 2389.8,
        "ema_fast": 2388.0,
        "ema_slow": 2384.0,
        "rsi": 61.0,
        "atr": 3.2,
        "volume_ratio": 1.1,
        "trend": "BULLISH",
        "volatility": "NORMAL",
        "regime": "TRENDING",
        **overrides,
    }
    return MarketIndicatorSnapshot(**values)


def test_trending_market_selects_highest_scoring_trend_strategy():
    result = StrategySelectionService().select(_snapshot(), session="London", spread_pips=2.1)

    assert result.selected_strategy_id == "evidence-trend-guard"
    assert result.candidates[0].recommendation == "SELECTED"
    assert result.candidates[0].score == 100
    assert "Market regime TRENDING" in result.candidates[0].matched_conditions
    assert result.candidates[-1].id == "range-mean-reversion"
    assert result.candidates[-1].recommendation == "BLOCKED"


def test_ranging_market_selects_mean_reversion():
    result = StrategySelectionService().select(
        _snapshot(
            ema_fast=2385.0,
            ema_slow=2385.0,
            rsi=50.0,
            trend="NEUTRAL",
            volatility="LOW",
            regime="RANGING",
        ),
        session="Asia",
        spread_pips=1.5,
    )

    assert result.selected_strategy_id == "range-mean-reversion"
    assert result.candidates[0].recommendation == "SELECTED"


def test_normal_xauusd_spread_does_not_block_strategy_selection():
    result = StrategySelectionService().select(_snapshot(), spread_pips=25.0)

    assert result.selected_strategy_id == "evidence-trend-guard"
    assert "Spread 25.00 pips" in result.candidates[0].matched_conditions
    assert all(not any("exceeds" in blocker for blocker in candidate.blocked_by) for candidate in result.candidates)


def test_explicit_spread_ceiling_remains_available_for_strict_profiles():
    result = StrategySelectionService(maximum_spread_pips=3.0).select(
        _snapshot(), spread_pips=3.1,
    )

    assert result.selected_strategy_id is None
    assert "exceeds" in result.reason


def test_incomplete_indicators_fail_closed():
    result = StrategySelectionService().select(
        _snapshot(ready=False, ema_fast=None, ema_slow=None, rsi=None, atr=None, volume_ratio=None,
                  trend="UNKNOWN", volatility="UNKNOWN", regime="UNKNOWN"),
        spread_pips=1.0,
    )

    assert result.selected_strategy_id is None
    assert result.reason == "Indicator warmup is incomplete."
    assert all(candidate.recommendation == "BLOCKED" for candidate in result.candidates)


def test_auto_selection_cannot_change_risk_configuration():
    risk = FixedRiskConfiguration(
        risk_percent=0.5,
        stop_loss_distance=3.0,
        reward_ratio=2.0,
        max_daily_loss=2.0,
    )
    original = risk
    service = RiskProtectedStrategySelectionService(risk)

    first = service.select(_snapshot(), session="London", spread_pips=2.1)
    second = service.select(
        _snapshot(trend="NEUTRAL", volatility="LOW", regime="RANGING", rsi=50.0),
        session="Asia",
        spread_pips=1.0,
    )

    assert first.selected_strategy_id != second.selected_strategy_id
    assert service.risk_configuration is risk
    assert service.risk_configuration == original
    with pytest.raises(FrozenInstanceError):
        service.risk_configuration.risk_percent = 1.0
