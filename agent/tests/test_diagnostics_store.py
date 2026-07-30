"""Schema migration tests for the trade diagnostics store."""

from __future__ import annotations

import sqlite3

import pytest

from src.diagnostics.store import DiagnosticsStore


def test_creates_versioned_trade_schema_and_indexes(tmp_path):
    db_path = tmp_path / "diagnostics.db"
    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 3
        columns = {
            row["name"] for row in store._conn.execute("PRAGMA table_info(diagnostic_trades)")
        }
        assert {"ticket_id", "trend_status", "ema_alignment", "rsi_value", "atr_value", "market_regime", "trading_session", "suspected_reason", "entry_time", "entry_price", "exit_price", "exit_time", "updated_at"} <= columns
        indexes = {
            row["name"] for row in store._conn.execute("PRAGMA index_list(diagnostic_trades)")
        }
        assert "idx_diagnostic_trades_user_entry" in indexes
        assert "idx_diagnostic_trades_user_reason" in indexes


def test_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "diagnostics.db"
    DiagnosticsStore(db_path).close()
    with DiagnosticsStore(db_path) as reopened:
        assert reopened.schema_version == 3


def test_v1_database_upgrades_without_losing_trade(tmp_path):
    db_path = tmp_path / "v1.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE diagnostic_trades (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, ticket_id TEXT NOT NULL,
            pair TEXT NOT NULL DEFAULT 'XAUUSD', direction TEXT NOT NULL,
            trend_status TEXT NOT NULL, ema_alignment TEXT NOT NULL,
            rsi_value REAL NOT NULL, atr_value REAL NOT NULL,
            volume_status TEXT NOT NULL, market_regime TEXT NOT NULL,
            trading_session TEXT NOT NULL, result TEXT NOT NULL,
            suspected_reason TEXT, profit_loss REAL, entry_time TEXT NOT NULL,
            created_at TEXT NOT NULL, UNIQUE(user_id, ticket_id)
        );
        INSERT INTO diagnostic_trades VALUES (
            'trade_1','user_1','ticket_1','XAUUSD','BUY','BULLISH','BULLISH',
            61,2.5,'NORMAL','TRENDING','LONDON','TP',NULL,120,
            '2026-07-30T10:00:00Z','2026-07-30T10:00:00Z'
        );
        PRAGMA user_version=1;
        """
    )
    connection.close()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 3
        row = store._conn.execute(
            "SELECT ticket_id, updated_at FROM diagnostic_trades WHERE id='trade_1'"
        ).fetchone()
        assert row["ticket_id"] == "ticket_1"
        assert row["updated_at"] == "2026-07-30T10:00:00Z"


def test_custom_filter_schema_enforces_valid_json_and_unique_user_name(tmp_path):
    with DiagnosticsStore(tmp_path / "filters.db") as store:
        store._conn.execute(
            "INSERT INTO diagnostic_filter_presets VALUES (?,?,?,?,?,?)",
            ("filter_1", "alice", "Asia losses", '{"session":"ASIA"}', "now", "now"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO diagnostic_filter_presets VALUES (?,?,?,?,?,?)",
                ("filter_2", "alice", "Asia losses", "not-json", "now", "now"),
            )


def test_trade_constraints_reject_invalid_indicator_snapshot(tmp_path):
    with DiagnosticsStore(tmp_path / "diagnostics.db") as store:
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (
                    id, user_id, ticket_id, direction, trend_status, ema_alignment,
                    rsi_value, atr_value, volume_status, market_regime,
                    trading_session, result, entry_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("trade_1", "user_1", "ticket_1", "BUY", "BULLISH", "BULLISH", 101, 2.1, "NORMAL", "TRENDING", "LONDON", "TP", "2026-07-30T10:00:00Z", "2026-07-30T10:00:00Z"),
            )


def test_rejects_database_from_newer_schema(tmp_path):
    db_path = tmp_path / "future.db"
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA user_version=99")
    connection.close()
    with pytest.raises(RuntimeError, match="newer than supported"):
        DiagnosticsStore(db_path)