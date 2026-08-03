from dataclasses import FrozenInstanceError

import pytest

from src.trading.auto_trade import (
    BotConfigurationNotReadyError,
    BotExecutionConfigurationProvider,
)


class Source:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def get_auto_trade_configuration(self, user_id, config_id):
        self.calls.append((user_id, config_id))
        return self.values


def _configuration(**overrides):
    values = {
        "id": "config-1", "userId": "alice", "symbol": "XAUUSD",
        "timeframe": "M15", "strategy": "Evidence trend guard",
        "riskPerTrade": 0.5, "dailyLossLimit": 2.0, "paperMode": True,
        "robotControls": {
            "enabled": True, "lotSize": 0.05, "stopLossPips": 30,
            "takeProfitPips": 60,
        },
        "updatedAt": "2026-08-01T09:00:00Z",
    }
    values.update(overrides)
    return values


def test_provider_returns_versioned_immutable_execution_snapshot():
    source = Source(_configuration())
    configuration = BotExecutionConfigurationProvider(source).load("alice", "config-1")

    assert configuration.symbol == "XAUUSD"
    assert configuration.lot_size == 0.05
    assert configuration.version == "2026-08-01T09:00:00Z"
    assert source.calls == [("alice", "config-1")]
    with pytest.raises(FrozenInstanceError):
        configuration.lot_size = 1.0


def test_provider_fails_closed_for_missing_disabled_or_live_configuration():
    with pytest.raises(BotConfigurationNotReadyError, match="not found"):
        BotExecutionConfigurationProvider(Source(None)).load("alice", "missing")
    disabled = _configuration(robotControls={
        "enabled": False, "lotSize": 0.05, "stopLossPips": 30, "takeProfitPips": 60,
    })
    with pytest.raises(BotConfigurationNotReadyError, match="disabled"):
        BotExecutionConfigurationProvider(Source(disabled)).load("alice", "config-1")
    with pytest.raises(BotConfigurationNotReadyError, match="not authorized"):
        BotExecutionConfigurationProvider(Source(_configuration(paperMode=False))).load(
            "alice", "config-1",
        )


def test_live_configuration_requires_explicit_runtime_authorization():
    result = BotExecutionConfigurationProvider(
        Source(_configuration(paperMode=False)), allow_live=True,
    ).load("alice", "config-1")

    assert result.paper_mode is False


def test_provider_rejects_mismatched_configuration_ownership():
    with pytest.raises(BotConfigurationNotReadyError, match="ownership"):
        BotExecutionConfigurationProvider(Source(_configuration(userId="bob"))).load(
            "alice", "config-1",
        )
