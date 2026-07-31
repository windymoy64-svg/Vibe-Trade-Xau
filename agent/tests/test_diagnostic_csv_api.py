"""Contract tests for diagnostics CSV trade ingestion."""

from __future__ import annotations

from fastapi.testclient import TestClient

import api_server
import src.api.diagnostics_routes as diagnostics_routes
from src.diagnostics.store import DiagnosticsStore


HEADER = (
    "ticket_id,pair,entry_time,direction,result,market_regime,trading_session,"
    "trend_status,ema_alignment,rsi_value,atr_value,volume_status,"
    "suspected_reason,profit_loss,entry_price,exit_price,exit_time\n"
)
ROWS = (
    "XAU-1,XAUUSD,2026-07-31T08:00:00Z,BUY,SL,RANGING,ASIA,FLAT,MIXED,61,3.2,NORMAL,Counter-trend,-42.5,3300,3296,2026-07-31T09:00:00Z\n"
    "XAU-2,XAUUSD,2026-07-31T10:00:00Z,SELL,TP,TRENDING,LONDON,BEARISH,BEARISH,38,4.1,HIGH,,80,3305,3297,2026-07-31T11:00:00Z\n"
)


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


def _upload(client: TestClient, content: bytes, *, user_id: str = "alice", filename: str = "trades.csv"):
    return client.post(
        "/data-sources/csv",
        data={"user_id": user_id},
        files={"file": (filename, content, "text/csv")},
    )


def test_csv_import_creates_trades_and_accumulates_source_metrics(tmp_path, monkeypatch) -> None:
    client, db_path = _client(tmp_path, monkeypatch)

    response = _upload(client, (HEADER + ROWS).encode())

    assert response.status_code == 200
    assert response.json() == {"imported": 2, "skipped": 0, "totalRows": 2, "sourceId": "csv"}
    duplicate = _upload(client, (HEADER + ROWS).encode())
    assert duplicate.status_code == 200
    assert duplicate.json() == {"imported": 0, "skipped": 2, "totalRows": 2, "sourceId": "csv"}
    with DiagnosticsStore(db_path) as store:
        rows = store._conn.execute(
            "SELECT ticket_id, user_id FROM diagnostic_trades ORDER BY ticket_id"
        ).fetchall()
        assert [(row["ticket_id"], row["user_id"]) for row in rows] == [
            ("XAU-1", "alice"), ("XAU-2", "alice"),
        ]
        source = store._conn.execute(
            "SELECT status, imported_trades, last_sync_at FROM data_sources WHERE user_id='alice' AND id='csv'"
        ).fetchone()
        assert source["status"] == "CONNECTED"
        assert source["imported_trades"] == 2
        assert source["last_sync_at"]


def test_csv_import_rejects_invalid_batch_without_partial_writes(tmp_path, monkeypatch) -> None:
    client, db_path = _client(tmp_path, monkeypatch)
    invalid_rows = ROWS + (
        "XAU-3,XAUUSD,not-a-date,BUY,SL,RANGING,ASIA,FLAT,MIXED,200,3,NORMAL,,,,,\n"
    )

    response = _upload(client, (HEADER + invalid_rows).encode())

    assert response.status_code == 422
    assert "row 4" in response.json()["detail"]
    with DiagnosticsStore(db_path) as store:
        assert store._conn.execute("SELECT COUNT(*) FROM diagnostic_trades").fetchone()[0] == 0
        assert store._conn.execute("SELECT COUNT(*) FROM data_sources").fetchone()[0] == 0


def test_csv_import_validates_user_file_type_encoding_and_size(tmp_path, monkeypatch) -> None:
    client, _ = _client(tmp_path, monkeypatch)
    content = (HEADER + ROWS).encode()

    assert _upload(client, content, user_id="missing").status_code == 404
    assert _upload(client, content, filename="trades.txt").status_code == 400
    assert _upload(client, b"\xff\xfe", filename="trades.csv").status_code == 422
    assert _upload(client, b"ticket_id\n", filename="trades.csv").status_code == 422
    monkeypatch.setattr(diagnostics_routes, "_CSV_MAX_BYTES", 32)
    oversized = _upload(client, content)
    assert oversized.status_code == 413
