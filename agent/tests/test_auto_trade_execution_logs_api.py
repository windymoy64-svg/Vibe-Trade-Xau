from fastapi.testclient import TestClient

import api_server
from src.diagnostics.store import DiagnosticsStore


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "logs.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    with DiagnosticsStore(db_path) as store:
        store._conn.executemany(
            "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("alice", "alice@example.com", "Alice", "x" * 32, "now", "now", "now"),
                ("bob", "bob@example.com", "Bob", "x" * 32, "now", "now", "now"),
            ],
        )
        base = {
            "level": "SIGNAL", "status": "EXECUTED", "message": "Filled",
            "symbol": "XAUUSD", "direction": "BUY", "strategyId": "trend",
            "lotSize": 0.05, "price": 2389.8, "stopLoss": 2383.8,
            "takeProfit": 2401.8, "brokerOrderId": "1842", "errorCode": None,
        }
        store.append_auto_trade_execution_log("alice", {
            "id": "older", "timestamp": "2026-08-01T08:00:00+00:00", **base,
        })
        store.append_auto_trade_execution_log("alice", {
            "id": "latest", "timestamp": "2026-08-01T09:00:00+00:00",
            **{**base, "level": "RISK", "status": "REJECTED", "message": "Blocked"},
        })
        store.append_auto_trade_execution_log("bob", {
            "id": "private", "timestamp": "2026-08-01T10:00:00+00:00", **base,
        })
    return TestClient(api_server.app, client=("127.0.0.1", 50000))


def test_execution_log_history_is_newest_first_and_user_scoped(tmp_path, monkeypatch):
    response = _client(tmp_path, monkeypatch).get(
        "/auto-trade/execution-logs", params={"userId": "alice"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["latest", "older"]
    assert response.json()[1]["price"] == 2389.8


def test_execution_log_filters_and_period_validation(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    filtered = client.get(
        "/auto-trade/execution-logs",
        params={
            "userId": "alice", "status": "EXECUTED", "level": "SIGNAL",
            "symbol": "xauusd", "direction": "BUY",
            "start": "2026-08-01T07:00:00Z", "end": "2026-08-01T08:30:00Z",
        },
    )

    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == ["older"]
    assert client.get(
        "/auto-trade/execution-logs",
        params={
            "userId": "alice", "start": "2026-08-02T00:00:00Z",
            "end": "2026-08-01T00:00:00Z",
        },
    ).status_code == 422
    assert client.get(
        "/auto-trade/execution-logs", params={"userId": "alice", "status": "UNKNOWN"},
    ).status_code == 422
