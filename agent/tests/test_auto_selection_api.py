from datetime import datetime, timezone

from fastapi.testclient import TestClient

import api_server
from src.api.auto_selection_routes import auto_selection_status_store, publish_auto_selection_status
from src.trading.auto_selection import MarketIndicatorSnapshot, StrategySelectionService


def _snapshot(**overrides) -> MarketIndicatorSnapshot:
    values = {
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "timestamp": datetime(2026, 8, 1, 8, 45, tzinfo=timezone.utc),
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


def setup_function() -> None:
    auto_selection_status_store.clear()


def test_status_returns_latest_user_scoped_selection():
    alice_snapshot = _snapshot()
    alice_selection = StrategySelectionService().select(
        alice_snapshot, session="London", spread_pips=2.1,
    )
    publish_auto_selection_status(
        "alice", alice_snapshot, alice_selection, session="London", spread_pips=2.1,
    )
    bob_snapshot = _snapshot(symbol="EURUSD")
    publish_auto_selection_status(
        "bob",
        bob_snapshot,
        StrategySelectionService().select(bob_snapshot, session="Asia", spread_pips=1.0),
        session="Asia",
        spread_pips=1.0,
    )

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/auto-selection/status", params={"user_id": "alice", "symbol": "xauusd"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["modeEnabled"] is False
    assert payload["status"] == "READY"
    assert payload["symbol"] == "XAUUSD"
    assert payload["analysisTimeframe"] == "M15"
    assert payload["selectedStrategyId"] == "evidence-trend-guard"
    assert payload["marketContext"] == {
        "regime": "TRENDING", "trend": "BULLISH", "volatility": "NORMAL",
        "session": "LONDON", "spreadPips": 2.1, "close": 2389.8,
        "emaFast": 2388.0, "emaSlow": 2384.0, "rsi": 61.0, "atr": 3.2,
        "volumeRatio": 1.1, "barCount": 50,
    }
    assert payload["candidates"][0]["recommendation"] == "SELECTED"
    assert payload["candidates"][-1]["blockedBy"]


def test_status_reports_warmup_and_missing_evaluations():
    snapshot = _snapshot(
        ready=False, ema_fast=None, ema_slow=None, rsi=None, atr=None,
        volume_ratio=None, trend="UNKNOWN", volatility="UNKNOWN", regime="UNKNOWN",
    )
    selection = StrategySelectionService().select(snapshot, spread_pips=1.0)
    publish_auto_selection_status(
        "alice", snapshot, selection, session="unknown", spread_pips=1.0,
    )
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))

    response = client.get("/auto-selection/status?user_id=alice")
    missing = client.get("/auto-selection/status?user_id=bob")

    assert response.status_code == 200
    assert response.json()["status"] == "WARMING_UP"
    assert response.json()["selectedStrategyId"] is None
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Auto-selection status not found"


def test_status_validates_query_contract():
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/auto-selection/status?user_id=",
    )

    assert response.status_code == 422


def test_toggle_is_explicit_idempotent_and_user_scoped():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))

    enabled = client.post(
        "/auto-selection/toggle", json={"userId": "alice", "enabled": True},
    )
    repeated = client.post(
        "/auto-selection/toggle", json={"userId": "alice", "enabled": True},
    )

    assert enabled.status_code == 200
    assert enabled.json()["userId"] == "alice"
    assert enabled.json()["enabled"] is True
    assert enabled.json()["updatedAt"]
    assert repeated.status_code == 200
    assert auto_selection_status_store.mode("alice")[0] is True
    assert auto_selection_status_store.mode("bob") == (False, None)


def test_toggle_rejects_invalid_user_and_non_boolean_state():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))

    blank_user = client.post(
        "/auto-selection/toggle", json={"userId": "  ", "enabled": True},
    )
    invalid_state = client.post(
        "/auto-selection/toggle", json={"userId": "alice", "enabled": "yes"},
    )

    assert blank_user.status_code == 422
    assert invalid_state.status_code == 422
