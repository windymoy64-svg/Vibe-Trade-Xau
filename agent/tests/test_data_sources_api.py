"""Contract tests for diagnostics data-source connection metadata."""

from __future__ import annotations

from fastapi.testclient import TestClient

import api_server
from src.diagnostics.store import DiagnosticsStore


def _client_with_user(tmp_path, monkeypatch) -> tuple[TestClient, str]:
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    with DiagnosticsStore(db_path) as store:
        store._conn.execute(
            "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("alice", "alice@example.com", "Alice", "x" * 32, "now", "now", "now"),
        )
        store._conn.commit()
    return TestClient(api_server.app, client=("127.0.0.1", 50000)), str(db_path)


def test_connect_data_source_creates_and_reconnects_metadata(tmp_path, monkeypatch) -> None:
    client, db_path = _client_with_user(tmp_path, monkeypatch)
    payload = {
        "user_id": "alice",
        "id": "mt5",
        "name": " MetaTrader 5 ",
        "type": " Trading terminal ",
        "description": " XAUUSD trade evidence ",
        "coverage": ["Trade lifecycle", " RSI ", "RSI"],
    }

    response = client.post("/data-sources/connect", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "mt5"
    assert body["userId"] == "alice"
    assert body["name"] == "MetaTrader 5"
    assert body["type"] == "Trading terminal"
    assert body["status"] == "CONNECTED"
    assert body["coverage"] == ["Trade lifecycle", "RSI"]
    assert body["importedTrades"] == 0
    assert body["lastSyncAt"] is None

    reconnected = client.post(
        "/data-sources/connect",
        json={**payload, "name": "MT5 XAUUSD", "coverage": ["Trades"]},
    )
    assert reconnected.status_code == 200
    assert reconnected.json()["createdAt"] == body["createdAt"]
    with DiagnosticsStore(db_path) as store:
        assert store._conn.execute(
            "SELECT COUNT(*) FROM data_sources WHERE user_id='alice' AND id='mt5'"
        ).fetchone()[0] == 1


def test_connect_data_source_rejects_missing_user_invalid_input_and_secrets(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_user(tmp_path, monkeypatch)
    valid = {
        "user_id": "missing",
        "id": "mt5",
        "name": "MetaTrader 5",
        "type": "Trading terminal",
        "coverage": [],
    }
    assert client.post("/data-sources/connect", json=valid).status_code == 404
    assert client.post(
        "/data-sources/connect",
        json={**valid, "user_id": "alice", "id": "Bad Source"},
    ).status_code == 422
    assert client.post(
        "/data-sources/connect",
        json={**valid, "user_id": "alice", "apiKey": "must-not-be-accepted"},
    ).status_code == 422
    assert client.post(
        "/data-sources/connect",
        json={**valid, "user_id": "alice", "coverage": ["x" * 81]},
    ).status_code == 422
