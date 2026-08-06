"""Contract tests for the MT5 integration and MCP bridge endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from api_server import create_app


def get_test_client(tmp_path):
    """Helper to create isolated test client per function."""
    app = create_app(str(tmp_path / "diagnostics.db"))
    return TestClient(app, client=("127.0.0.1", 50000))


def test_post_execution_log_creates_entry(tmp_path):
    """POST /execution-log creates an execution audit entry."""
    client = get_test_client(tmp_path)
    
    response = client.post(
        "/execution-log",
        json={
            "executionSource": "MANUAL",
            "orderType": "BUY",
            "symbol": "XAUUSD",
            "volume": 0.10,
            "price": 2345.50,
            "stopLoss": 2340.00,
            "takeProfit": 2355.00,
            "status": "EXECUTED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "id" in payload or "logId" in payload or payload.get("success") is True


def test_post_execution_log_rejects_invalid_payload(tmp_path):
    """POST validation rejects missing required fields and invalid ranges."""
    client = get_test_client(tmp_path)
    
    no_source = client.post(
        "/execution-log",
        json={"orderType": "BUY"},
    )
    assert no_source.status_code == 422
    
    invalid_volume = client.post(
        "/execution-log",
        json={
            "executionSource": "AUTO_BY_AI",
            "orderType": "SELL",
            "symbol": "EURUSD",
            "volume": 0.0,
            "status": "PENDING",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert invalid_volume.status_code == 422


def test_get_execution_logs_returns_empty_list(tmp_path):
    """GET empty logs returns array without entries."""
    client = get_test_client(tmp_path)
    
    response = client.get("/execution-log")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_execution_logs_with_filters(tmp_path):
    """GET with source/status/symbol filters queries correctly."""
    client = get_test_client(tmp_path)
    
    # Create some logs first
    for i in range(3):
        client.post(
            "/execution-log",
            json={
                "executionSource": "MANUAL" if i % 2 == 0 else "AUTO_BY_AI",
                "orderType": "BUY",
                "symbol": "XAUUSD",
                "volume": 0.10,
                "status": "EXECUTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    
    all_logs = client.get("/execution-log")
    assert all_logs.status_code == 200
    assert len(all_logs.json()) == 3
    
    manual_only = client.get("/execution-log?source=MANUAL&limit=10")
    assert manual_only.status_code == 200
    assert len(manual_only.json()) == 2


def test_limit_parameter_enforces_bounds(tmp_path):
    """Limit query parameter enforces minimum and maximum boundaries."""
    client = get_test_client(tmp_path)
    
    too_low = client.get("/execution-log?limit=0")
    assert too_low.status_code == 422
    
    too_high = client.get("/execution-log?limit=201")
    assert too_high.status_code == 422
    
    valid = client.get("/execution-log?limit=5")
    assert valid.status_code == 200


def test_post_token_generate_creates_mcp_token(tmp_path):
    """POST /token/generate creates new token with custom expiry."""
    client = get_test_client(tmp_path)
    
    response = client.post("/token/generate", params={"expires_hours": 48})
    assert response.status_code == 200
    payload = response.json()
    assert "tokenId" in payload or "token_id" in payload
    assert payload.get("userId") == "user-123"
    assert "expiresAt" in payload or "expires_at" in payload
    assert "createdAt" in payload or "created_at" in payload


def test_active_mcp_token_survives_client_refresh(tmp_path):
    """GET /token/active restores the latest valid token metadata."""
    client = get_test_client(tmp_path)

    generated = client.post("/mt5/token/generate", params={"expires_hours": 48})
    assert generated.status_code == 200
    token_id = generated.json()["tokenId"]

    active = client.get("/mt5/token/active")
    assert active.status_code == 200
    assert active.json()["tokenId"] == token_id
    assert active.json()["isValid"] is True

    assert client.delete(f"/mt5/token/{token_id}").status_code == 204
    assert client.get("/mt5/token/active").json() is None


def test_post_token_generate_validates_expiry_range(tmp_path):
    """Token generation rejects out-of-range expiry hours."""
    client = get_test_client(tmp_path)
    
    too_short = client.post("/token/generate", params={"expires_hours": 0})
    assert too_short.status_code == 422
    
    too_long = client.post("/token/generate", params={"expires_hours": 721})
    assert too_long.status_code == 422
    
    default_24h = client.post("/token/generate")
    assert default_24h.status_code == 200


def test_get_connection_status_returns_health_snapshot(tmp_path):
    """GET /connection/status returns connection health summary."""
    client = get_test_client(tmp_path)
    
    response = client.get("/connection/status")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload.get("userId") == "user-123"
    assert isinstance(payload.get("terminalConnected"), bool)
    assert isinstance(payload.get("positionsCount"), int)


def test_get_mock_ohlc_returns_live_tick_data(tmp_path):
    """GET /live/ohc/mock returns simulated OHLC tick bar."""
    client = get_test_client(tmp_path)
    
    response = client.get("/live/ohlc/mock?symbol=XAUUSD")
    assert response.status_code == 200
    payload = response.json()
    assert "open" in payload
    assert "high" in payload
    assert "low" in payload
    assert "close" in payload
    assert "volume" in payload
    assert "timestamp" in payload


def test_all_route_paths_are_registered(tmp_path):
    """Verify all MT5 routes are registered on FastAPI app."""
    app = create_app(str(tmp_path / "diagnostics.db"))
    paths = [route.path for route in app.routes if hasattr(route, "path")]
    
    expected_paths = [
        "/execution-log",
        "/token/generate",
        "/connection/status",
        "/live/ohlc/mock",
        "/mt5/live/snapshot",
        "/mt5/token/{token_id}",
    ]
    
    for path in expected_paths:
        assert any(path in p for p in paths), f"Route {path} not found"


def test_live_snapshot_fails_closed_without_terminal(tmp_path, monkeypatch):
    """Realtime endpoint reports 503 instead of returning preview market data."""
    monkeypatch.setattr(
        "src.mt5_integration.service.MTPyBridgeService.live_snapshot",
        lambda self, user_id, symbol, timeframe, limit: {
            "status": "error", "connected": False, "error": "terminal offline",
        },
    )
    response = get_test_client(tmp_path).get("/mt5/live/snapshot?symbol=XAUUSD&timeframe=M30")
    assert response.status_code == 503
    assert response.json()["detail"]["connected"] is False


def test_mcp_token_can_be_revoked(tmp_path):
    client = get_test_client(tmp_path)
    token = client.post("/mt5/token/generate").json()["tokenId"]
    assert client.delete(f"/mt5/token/{token}").status_code == 204
    # Revoke is intentionally idempotent so EA/network retries remain safe.
    assert client.delete(f"/mt5/token/{token}").status_code == 204


def test_dashboard_can_save_redacted_mt5_configuration(tmp_path, monkeypatch):
    from src.trading.connectors.mt5 import _client

    monkeypatch.setattr(_client, "config_path", lambda: tmp_path / "mt5.json")
    client = get_test_client(tmp_path)
    payload = {
        "login": 12345678, "password": "demo-secret", "server": "Broker-Demo",
        "terminalPath": "", "profile": "paper", "symbolSuffix": "m",
        "timeout": 15, "maxOrderVolume": 0.1, "maxOrderNotionalUsd": 10000,
    }
    saved = client.put("/mt5/configuration", json=payload)
    assert saved.status_code == 200
    assert saved.json()["passwordConfigured"] is True
    assert "password" not in saved.json()
    assert "demo-secret" not in saved.text

    payload["password"] = ""
    assert client.put("/mt5/configuration", json=payload).status_code == 200
    assert _client.load_config().password == "demo-secret"


def test_execution_log_error_codes_are_validated(tmp_path):
    """Error code field validates range constraints (-10000 to 0)."""
    client = get_test_client(tmp_path)
    
    valid_error = client.post(
        "/execution-log",
        json={
            "executionSource": "AUTO_BY_AI",
            "orderType": "BUY",
            "symbol": "XAUUSD",
            "volume": 0.10,
            "status": "FAILED",
            "errorCode": -5000,
            "errorMessage": "Test error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert valid_error.status_code == 200
    
    out_of_range = client.post(
        "/execution-log",
        json={
            "executionSource": "MANUAL",
            "orderType": "SELL",
            "symbol": "EURUSD",
            "volume": 0.10,
            "status": "FAILED",
            "errorCode": -10001,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert out_of_range.status_code == 422


def test_token_validation_in_response_field(tmp_path):
    """Generated token response includes isValid boolean field."""
    client = get_test_client(tmp_path)
    
    response = client.post("/token/generate")
    assert response.status_code == 200
    payload = response.json()
    # Check both camelCase (from TokenGenerateResponse) and snake_case (from service metadata)
    assert "isValid" in payload or "is_valid" in payload
