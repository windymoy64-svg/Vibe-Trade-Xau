"""Schema migration tests for the trade diagnostics store."""

from __future__ import annotations

import sqlite3

import pytest

from src.diagnostics.store import DiagnosticsStore


def test_creates_versioned_trade_schema_and_indexes(tmp_path):
    db_path = tmp_path / "diagnostics.db"
    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 7
        columns = {
            row["name"] for row in store._conn.execute("PRAGMA table_info(diagnostic_trades)")
        }
        assert {"ticket_id", "trend_status", "ema_alignment", "rsi_value", "atr_value", "market_regime", "trading_session", "suspected_reason", "entry_time", "entry_price", "exit_price", "exit_time", "updated_at"} <= columns
        indexes = {
            row["name"] for row in store._conn.execute("PRAGMA index_list(diagnostic_trades)")
        }
        assert "idx_diagnostic_trades_user_entry" in indexes
        assert "idx_diagnostic_trades_user_reason" in indexes
        pattern_columns = {
            row["name"] for row in store._conn.execute("PRAGMA table_info(pola_kekalahan)")
        }
        assert {
            "user_id", "name", "category", "description", "loss_count",
            "loss_percentage", "confidence", "severity", "evidence_trade_ids_json",
            "trend_delta", "period_start", "period_end", "generated_at",
            "created_at", "updated_at",
        } <= pattern_columns
        pattern_indexes = {
            row["name"] for row in store._conn.execute("PRAGMA index_list(pola_kekalahan)")
        }
        assert "idx_pola_kekalahan_user_period" in pattern_indexes
        assert "idx_pola_kekalahan_user_severity" in pattern_indexes
        status_columns = {
            row["name"]
            for row in store._conn.execute(
                "PRAGMA table_info(diagnostic_recommendation_statuses)"
            )
        }
        assert {"user_id", "recommendation_id", "status", "applied_at", "updated_at"} <= status_columns
        recommendation_columns = {
            row["name"]
            for row in store._conn.execute(
                "PRAGMA table_info(diagnostic_recommendations)"
            )
        }
        assert {
            "id", "user_id", "title", "summary", "action", "pattern_id",
            "pattern_name", "priority", "status", "expected_impact",
            "evidence_losses", "confidence", "effort", "steps_json",
            "validation_target", "guardrail", "generated_at", "created_at",
            "updated_at",
        } <= recommendation_columns
        recommendation_indexes = {
            row["name"]
            for row in store._conn.execute(
                "PRAGMA index_list(diagnostic_recommendations)"
            )
        }
        assert "idx_recommendations_user_priority" in recommendation_indexes
        assert "idx_recommendations_user_status" in recommendation_indexes
        improvement_columns = {
            row["name"]
            for row in store._conn.execute("PRAGMA table_info(improvement_logs)")
        }
        assert {
            "id", "user_id", "recommendation_id", "title", "change_description",
            "status", "baseline_loss_rate", "target_loss_rate", "current_loss_rate",
            "validation_start", "validation_end", "applied_at", "owner", "notes",
            "created_at", "updated_at",
        } <= improvement_columns
        improvement_indexes = {
            row["name"]
            for row in store._conn.execute("PRAGMA index_list(improvement_logs)")
        }
        assert {
            "idx_improvement_logs_user_status",
            "idx_improvement_logs_user_applied",
            "idx_improvement_logs_user_recommendation",
        } <= improvement_indexes


def test_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "diagnostics.db"
    DiagnosticsStore(db_path).close()
    with DiagnosticsStore(db_path) as reopened:
        assert reopened.schema_version == 7


def test_v5_database_upgrades_recommendations_without_losing_status(tmp_path):
    db_path = tmp_path / "v5.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE diagnostic_recommendation_statuses (
            user_id TEXT NOT NULL,
            recommendation_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status = 'APPLIED'),
            applied_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, recommendation_id)
        );
        INSERT INTO diagnostic_recommendation_statuses VALUES
            ('alice', 'rec_existing', 'APPLIED', 'now', 'now');
        PRAGMA user_version=5;
        """
    )
    connection.close()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 7
        assert store.recommendation_statuses("alice") == {
            "rec_existing": "APPLIED",
        }
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='diagnostic_recommendations'"
        ).fetchone()["name"] == "diagnostic_recommendations"


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
        assert store.schema_version == 7
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


def test_v3_database_upgrades_with_loss_pattern_schema(tmp_path):
    db_path = tmp_path / "v3.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE diagnostic_trades (id TEXT PRIMARY KEY);
        CREATE TABLE diagnostic_filter_presets (id TEXT PRIMARY KEY);
        INSERT INTO diagnostic_trades VALUES ('trade_existing');
        PRAGMA user_version=3;
        """
    )
    connection.close()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 7
        assert store._conn.execute(
            "SELECT id FROM diagnostic_trades WHERE id='trade_existing'"
        ).fetchone()["id"] == "trade_existing"
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pola_kekalahan'"
        ).fetchone()["name"] == "pola_kekalahan"


def test_loss_pattern_schema_enforces_analytics_constraints(tmp_path):
    values = (
        "pattern_1", "alice", "Counter-trend entry", "TREND", "Description",
        12, 60.0, 91.0, "HIGH", '["trade_1"]', -5.0,
        "2026-07-01T00:00:00Z", "2026-07-31T23:59:59Z",
        "2026-07-31T23:59:59Z", "now", "now",
    )
    with DiagnosticsStore(tmp_path / "patterns.db") as store:
        store._conn.execute(
            "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            values,
        )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("pattern_2", *values[1:8], "not-json", *values[9:]),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("pattern_3", *values[1:6], 101.0, *values[7:]),
            )


def test_recommendation_status_override_is_user_scoped_and_reopenable(tmp_path):
    with DiagnosticsStore(tmp_path / "recommendations.db") as store:
        store.set_recommendation_applied("alice", "rec_pattern", True)
        assert store.recommendation_statuses("alice") == {"rec_pattern": "APPLIED"}
        assert store.recommendation_statuses("bob") == {}

        store.set_recommendation_applied("alice", "rec_pattern", False)
        assert store.recommendation_statuses("alice") == {}


def test_recommendation_schema_enforces_contract_and_user_identity(tmp_path):
    values = (
        "rec_1", "alice", "Title", "Summary", "Action", "pattern_1",
        "Pattern", "HIGH", "READY", 12.5, 4, 88.0, "MEDIUM",
        '["step"]', "Target", "Guardrail", "2026-07-31", "now", "now",
    )
    with DiagnosticsStore(tmp_path / "recommendations.db") as store:
        store._conn.execute(
            "INSERT INTO diagnostic_recommendations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            values,
        )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO diagnostic_recommendations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("rec_2", *values[1:7], "LOW", *values[8:]),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO diagnostic_recommendations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("rec_3", *values[1:13], "not-json", *values[14:]),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO diagnostic_recommendations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("rec_1", *values[1:]),
            )


def test_v6_database_upgrades_with_improvement_log_schema(tmp_path):
    db_path = tmp_path / "v6.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE diagnostic_recommendations (id TEXT PRIMARY KEY);
        INSERT INTO diagnostic_recommendations VALUES ('rec_existing');
        PRAGMA user_version=6;
        """
    )
    connection.close()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 7
        assert store._conn.execute(
            "SELECT id FROM diagnostic_recommendations WHERE id='rec_existing'"
        ).fetchone()["id"] == "rec_existing"
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='improvement_logs'"
        ).fetchone()["name"] == "improvement_logs"


def test_improvement_log_schema_enforces_lifecycle_and_validation_contract(tmp_path):
    valid = (
        "improvement_1", "alice", "rec_pattern", "Trend gate",
        "Require aligned trend confirmation", "MONITORING", 45.2, 30.0, 37.1,
        "2026-07-01", "2026-07-31", "2026-07-15", "Strategy team",
        "Monitoring weekly evidence", "2026-07-15T00:00:00Z", "2026-07-31T00:00:00Z",
    )
    statement = "INSERT INTO improvement_logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    with DiagnosticsStore(tmp_path / "improvements.db") as store:
        store._conn.execute(statement, valid)

        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(statement, ("improvement_2", *valid[1:5], "UNKNOWN", *valid[6:]))
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(statement, ("improvement_3", *valid[1:6], 101.0, *valid[7:]))
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                statement,
                ("improvement_4", *valid[1:9], "2026-08-01", "2026-07-31", *valid[11:]),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(statement, ("improvement_1", *valid[1:]))


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