"""Contract tests for user-scoped diagnostic notifications."""

from fastapi.testclient import TestClient

import api_server
from src.diagnostics.store import DiagnosticsStore


def _seed(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    with DiagnosticsStore(db_path) as store:
        store._conn.executemany(
            "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("alice", "alice@example.com", "Alice", "x" * 32, "now", "now", "now"),
                ("bob", "bob@example.com", "Bob", "x" * 32, "now", "now", "now"),
            ],
        )
        store._conn.executemany(
            """INSERT INTO notifications (
                id, user_id, notification_type, title, detail, href, is_read,
                read_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("older", "alice", "PATTERN", "Older pattern", "Details", "/diagnostics/patterns", 1, "2026-08-01T08:30:00Z", "2026-08-01T08:00:00Z", "now"),
                ("latest", "alice", "RECOMMENDATION", "Latest action", "Review it", "/diagnostics/recommendations", 0, None, "2026-08-01T09:00:00Z", "now"),
                ("private", "bob", "VALIDATION", "Bob only", "Hidden", "/diagnostics/improvements", 0, None, "2026-08-01T10:00:00Z", "now"),
            ],
        )
        store._conn.commit()
    return TestClient(api_server.app, client=("127.0.0.1", 50000))


def test_notifications_are_newest_first_and_user_scoped(tmp_path, monkeypatch):
    response = _seed(tmp_path, monkeypatch).get(
        "/notifications", params={"user_id": "alice"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "latest", "type": "RECOMMENDATION", "title": "Latest action",
            "detail": "Review it", "createdAt": "2026-08-01T09:00:00Z",
            "href": "/diagnostics/recommendations", "read": False,
        },
        {
            "id": "older", "type": "PATTERN", "title": "Older pattern",
            "detail": "Details", "createdAt": "2026-08-01T08:00:00Z",
            "href": "/diagnostics/patterns", "read": True,
        },
    ]


def test_notifications_support_unread_filter_limit_and_missing_user(tmp_path, monkeypatch):
    client = _seed(tmp_path, monkeypatch)

    unread = client.get(
        "/notifications", params={"user_id": "alice", "unread_only": True, "limit": 1},
    )

    assert unread.status_code == 200
    assert [item["id"] for item in unread.json()] == ["latest"]
    assert client.get("/notifications", params={"user_id": "missing"}).status_code == 404
    assert client.get("/notifications", params={"user_id": "alice", "limit": 0}).status_code == 422
