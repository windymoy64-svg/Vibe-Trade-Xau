"""Contract tests for user notification preferences."""

from __future__ import annotations

from fastapi.testclient import TestClient

import api_server
from src.diagnostics.store import DiagnosticsStore


DEFAULTS = {
    "inApp": True,
    "email": True,
    "mobile": False,
    "criticalPatterns": True,
    "recommendations": True,
    "validationResults": True,
    "sourceHealth": True,
    "weeklyDigest": False,
    "quietHours": True,
    "quietStart": "22:00",
    "quietEnd": "07:00",
}


def _client(tmp_path, monkeypatch) -> tuple[TestClient, str]:
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    with DiagnosticsStore(db_path) as store:
        store._conn.execute(
            "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("alice", "alice@example.com", "Alice", "x" * 32, "now", "now", "now"),
        )
        store._conn.commit()
    return TestClient(api_server.app, client=("127.0.0.1", 50000)), str(db_path)


def test_get_returns_defaults_and_put_persists_complete_preferences(tmp_path, monkeypatch) -> None:
    client, db_path = _client(tmp_path, monkeypatch)

    response = client.get("/user/notifications", params={"user_id": "alice"})
    assert response.status_code == 200
    assert response.json() == DEFAULTS

    changed = {
        **DEFAULTS,
        "email": False,
        "mobile": True,
        "weeklyDigest": True,
        "quietStart": "23:30",
        "quietEnd": "06:15",
    }
    updated = client.put(
        "/user/notifications",
        params={"user_id": "alice"},
        json=changed,
    )
    assert updated.status_code == 200
    assert updated.json() == changed
    assert client.get("/user/notifications", params={"user_id": "alice"}).json() == changed
    with DiagnosticsStore(db_path) as store:
        assert store._conn.execute(
            "SELECT COUNT(*) FROM notification_preferences WHERE user_id='alice'"
        ).fetchone()[0] == 1


def test_notification_preferences_validate_user_and_quiet_hours(tmp_path, monkeypatch) -> None:
    client, _ = _client(tmp_path, monkeypatch)
    assert client.get("/user/notifications", params={"user_id": "missing"}).status_code == 404
    assert client.get("/user/notifications").status_code == 422
    assert client.put(
        "/user/notifications",
        params={"user_id": "missing"},
        json=DEFAULTS,
    ).status_code == 404
    for invalid in ("24:00", "7:00", "12:60", "noon"):
        response = client.put(
            "/user/notifications",
            params={"user_id": "alice"},
            json={**DEFAULTS, "quietStart": invalid},
        )
        assert response.status_code == 422
