"""Schema migration tests for the trade diagnostics store."""

from __future__ import annotations

import sqlite3

import pytest

from src.diagnostics.store import (
    DiagnosticDataSource,
    DiagnosticNotification,
    DiagnosticUser,
    DiagnosticsStore,
)


def test_creates_versioned_trade_schema_and_indexes(tmp_path):
    db_path = tmp_path / "diagnostics.db"
    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 11
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
        user_columns = {
            row["name"] for row in store._conn.execute("PRAGMA table_info(users)")
        }
        assert {
            "id", "email", "name", "password_hash", "role", "timezone",
            "trading_focus", "bio", "created_at", "updated_at", "last_active_at",
        } <= user_columns
        user_indexes = {
            row["name"] for row in store._conn.execute("PRAGMA index_list(users)")
        }
        assert "idx_users_updated_at" in user_indexes
        data_source_columns = {
            row["name"] for row in store._conn.execute("PRAGMA table_info(data_sources)")
        }
        assert {
            "id", "user_id", "name", "source_type", "description", "status",
            "last_sync_at", "imported_trades", "coverage_json", "created_at", "updated_at",
        } <= data_source_columns
        data_source_indexes = {
            row["name"] for row in store._conn.execute("PRAGMA index_list(data_sources)")
        }
        assert {
            "idx_data_sources_user_status", "idx_data_sources_user_sync",
        } <= data_source_indexes
        notification_columns = {
            row["name"] for row in store._conn.execute("PRAGMA table_info(notifications)")
        }
        assert {
            "id", "user_id", "notification_type", "title", "detail", "href",
            "is_read", "read_at", "created_at", "updated_at",
        } <= notification_columns
        notification_indexes = {
            row["name"] for row in store._conn.execute("PRAGMA index_list(notifications)")
        }
        assert {
            "idx_notifications_user_created", "idx_notifications_user_unread",
        } <= notification_indexes
        preference_columns = {
            row["name"]
            for row in store._conn.execute("PRAGMA table_info(notification_preferences)")
        }
        assert {
            "user_id", "in_app", "email", "mobile", "critical_patterns",
            "recommendations", "validation_results", "source_health", "weekly_digest",
            "quiet_hours", "quiet_start", "quiet_end", "created_at", "updated_at",
        } <= preference_columns
        assert {
            "idx_improvement_logs_user_status",
            "idx_improvement_logs_user_applied",
            "idx_improvement_logs_user_recommendation",
        } <= improvement_indexes


def test_migration_is_idempotent(tmp_path):
    db_path = tmp_path / "diagnostics.db"
    DiagnosticsStore(db_path).close()
    with DiagnosticsStore(db_path) as reopened:
        assert reopened.schema_version == 11


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
        assert store.schema_version == 11
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
        assert store.schema_version == 11
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
        assert store.schema_version == 11
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
        assert store.schema_version == 11
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


def test_user_model_and_schema_enforce_account_contract(tmp_path):
    user = DiagnosticUser(
        id="user_1",
        email="trader@example.com",
        name="Alex Morgan",
        password_hash="scrypt$16384$8$1$" + "a" * 32 + "$" + "b" * 128,
        role="Strategy owner",
        timezone="UTC",
        trading_focus="XAUUSD intraday",
        bio="Evidence-led diagnostics",
        created_at="2026-07-31T00:00:00Z",
        updated_at="2026-07-31T00:00:00Z",
        last_active_at="2026-07-31T00:00:00Z",
    )
    assert user.email == "trader@example.com"

    with DiagnosticsStore(tmp_path / "users.db") as store:
        store._conn.execute(
            """INSERT INTO users (
                id, email, name, password_hash, role, timezone, trading_focus,
                bio, created_at, updated_at, last_active_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user.id, user.email, user.name, user.password_hash, user.role,
                user.timezone, user.trading_focus, user.bio, user.created_at,
                user.updated_at, user.last_active_at,
            ),
        )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("user_2", "TRADER@example.com", "Other User", "x" * 32, "now", "now", "now"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("user_3", "valid@example.com", "A", "x" * 32, "now", "now", "now"),
            )


def test_v7_database_upgrades_with_users_schema(tmp_path):
    db_path = tmp_path / "v7.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE diagnostic_trades (id TEXT PRIMARY KEY);
        INSERT INTO diagnostic_trades VALUES ('trade_existing');
        PRAGMA user_version=7;
        """
    )
    connection.close()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 11
        assert store._conn.execute(
            "SELECT id FROM diagnostic_trades WHERE id='trade_existing'"
        ).fetchone()["id"] == "trade_existing"
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()["name"] == "users"

        # Re-opening must not recreate or damage the user table/index.
    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 11
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_updated_at'"
        ).fetchone()["name"] == "idx_users_updated_at"


def test_data_source_model_and_schema_enforce_metadata_contract(tmp_path):
    source = DiagnosticDataSource(
        id="mt5",
        user_id="user_1",
        name="MetaTrader 5",
        source_type="Trading terminal",
        description="Closed trades and entry snapshots",
        status="CONNECTED",
        last_sync_at="2026-07-31T08:24:00Z",
        imported_trades=1248,
        coverage_json='["Trade lifecycle", "RSI"]',
        created_at="2026-07-31T00:00:00Z",
        updated_at="2026-07-31T08:24:00Z",
    )
    assert source.id == "mt5"

    with DiagnosticsStore(tmp_path / "data-sources.db") as store:
        store._conn.execute(
            """INSERT INTO users (
                id, email, name, password_hash, created_at, updated_at, last_active_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("user_1", "trader@example.com", "Alex Morgan", "x" * 32, "now", "now", "now"),
        )
        store._conn.execute(
            """INSERT INTO data_sources (
                id, user_id, name, source_type, description, status, last_sync_at,
                imported_trades, coverage_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source.id, source.user_id, source.name, source.source_type,
                source.description, source.status, source.last_sync_at,
                source.imported_trades, source.coverage_json, source.created_at,
                source.updated_at,
            ),
        )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO data_sources (id, user_id, name, source_type, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("mt5", "user_1", "Duplicate", "Trading terminal", "AVAILABLE", "now", "now"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO data_sources (id, user_id, name, source_type, status, imported_trades, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("csv", "user_1", "CSV", "File upload", "INVALID", 0, "now", "now"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO data_sources (id, user_id, name, source_type, status, imported_trades, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("webhook", "user_1", "Webhook", "REST API", "AVAILABLE", -1, "now", "now"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO data_sources (id, user_id, name, source_type, status, coverage_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("bad", "user_1", "Bad", "REST API", "AVAILABLE", "not-json", "now", "now"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "INSERT INTO data_sources (id, user_id, name, source_type, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("orphan", "missing", "Orphan", "REST API", "AVAILABLE", "now", "now"),
            )
        store._conn.execute("DELETE FROM users WHERE id = ?", ("user_1",))
        assert store._conn.execute("SELECT COUNT(*) FROM data_sources").fetchone()[0] == 0


def test_v8_database_upgrades_with_data_sources_schema(tmp_path):
    db_path = tmp_path / "v8.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT '',
            timezone TEXT NOT NULL DEFAULT 'UTC',
            trading_focus TEXT NOT NULL DEFAULT '',
            bio TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_active_at TEXT NOT NULL
        );
        INSERT INTO users (
            id, email, name, password_hash, created_at, updated_at, last_active_at
        ) VALUES (
            'user_1', 'trader@example.com', 'Alex Morgan',
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', 'now', 'now', 'now'
        );
        PRAGMA user_version=8;
        """
    )
    connection.close()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 11
        assert store._conn.execute(
            "SELECT email FROM users WHERE id='user_1'"
        ).fetchone()["email"] == "trader@example.com"
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='data_sources'"
        ).fetchone()["name"] == "data_sources"
        store._conn.execute(
            "INSERT INTO data_sources (id, user_id, name, source_type, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("csv", "user_1", "CSV", "File upload", "AVAILABLE", "now", "now"),
        )
        store._conn.commit()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 10
        assert store._conn.execute(
            "SELECT name FROM data_sources WHERE id='csv' AND user_id='user_1'"
        ).fetchone()["name"] == "CSV"


def test_connect_data_source_upserts_user_scoped_metadata(tmp_path):
    with DiagnosticsStore(tmp_path / "connect.db") as store:
        for user_id, email in (("alice", "alice@example.com"), ("bob", "bob@example.com")):
            store._conn.execute(
                "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, email, user_id.title(), "x" * 32, "now", "now", "now"),
            )
        alice = store.connect_data_source(
            user_id="alice", source_id="mt5", name="MetaTrader 5",
            source_type="Trading terminal", description="Initial", coverage=["Trades"],
        )
        bob = store.connect_data_source(
            user_id="bob", source_id="mt5", name="MetaTrader 5",
            source_type="Trading terminal", description="Bob source", coverage=["Trades"],
        )
        assert alice is not None and bob is not None
        created_at = alice["createdAt"]
        store._conn.execute(
            "UPDATE data_sources SET imported_trades = 12, last_sync_at = 'sync' WHERE user_id='alice' AND id='mt5'"
        )
        reconnected = store.connect_data_source(
            user_id="alice", source_id="mt5", name="MT5 XAUUSD",
            source_type="Trading terminal", description="Updated", coverage=["Trades", "RSI"],
        )
        assert reconnected is not None
        assert reconnected["name"] == "MT5 XAUUSD"
        assert reconnected["status"] == "CONNECTED"
        assert reconnected["importedTrades"] == 12
        assert reconnected["lastSyncAt"] == "sync"
        assert reconnected["createdAt"] == created_at
        assert reconnected["coverage"] == ["Trades", "RSI"]
        assert store._conn.execute("SELECT COUNT(*) FROM data_sources").fetchone()[0] == 2
        assert store.connect_data_source(
            user_id="missing", source_id="mt5", name="MT5",
            source_type="Trading terminal", description="", coverage=[],
        ) is None


def test_notification_model_and_schema_enforce_read_contract(tmp_path):
    notification = DiagnosticNotification(
        id="notification-pattern",
        user_id="alice",
        notification_type="PATTERN",
        title="New dominant loss pattern",
        detail="Counter-trend entries crossed the severity threshold.",
        href="/diagnostics/patterns",
        is_read=False,
        read_at=None,
        created_at="2026-07-31T08:20:00Z",
        updated_at="2026-07-31T08:20:00Z",
    )
    assert notification.notification_type == "PATTERN"

    with DiagnosticsStore(tmp_path / "notifications.db") as store:
        for user_id, email in (("alice", "alice@example.com"), ("bob", "bob@example.com")):
            store._conn.execute(
                "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, email, user_id.title(), "x" * 32, "now", "now", "now"),
            )
        statement = """INSERT INTO notifications (
            id, user_id, notification_type, title, detail, href, is_read,
            read_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        values = (
            notification.id, notification.user_id, notification.notification_type,
            notification.title, notification.detail, notification.href, 0,
            notification.read_at, notification.created_at, notification.updated_at,
        )
        store._conn.execute(statement, values)
        store._conn.execute(statement, (values[0], "bob", *values[2:]))
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(statement, ("bad-type", "alice", "SOURCE", *values[3:]))
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(statement, ("external", "alice", *values[2:5], "https://evil.example", *values[6:]))
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(statement, ("protocol", "alice", *values[2:5], "//evil.example", *values[6:]))
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(statement, ("read-missing-time", "alice", *values[2:6], 1, None, *values[8:]))
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(statement, ("unread-with-time", "alice", *values[2:6], 0, "now", *values[8:]))
        store._conn.execute("DELETE FROM users WHERE id='alice'")
        assert store._conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id='alice'"
        ).fetchone()[0] == 0
        assert store._conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id='bob'"
        ).fetchone()[0] == 1


def test_v9_database_upgrades_with_notifications_schema(tmp_path):
    db_path = tmp_path / "v9.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        PRAGMA foreign_keys=ON;
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_active_at TEXT NOT NULL
        );
        CREATE TABLE data_sources (
            id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, id)
        );
        INSERT INTO users VALUES (
            'alice', 'alice@example.com', 'Alice',
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', 'now', 'now', 'now'
        );
        INSERT INTO data_sources VALUES (
            'csv', 'alice', 'CSV', 'File upload', 'CONNECTED', 'now', 'now'
        );
        PRAGMA user_version=9;
        """
    )
    connection.close()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 10
        assert store._conn.execute(
            "SELECT name FROM data_sources WHERE user_id='alice' AND id='csv'"
        ).fetchone()["name"] == "CSV"
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'"
        ).fetchone()["name"] == "notifications"

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 10
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_notifications_user_unread'"
        ).fetchone()["name"] == "idx_notifications_user_unread"


def test_notification_preferences_schema_constraints_and_cascade(tmp_path):
    with DiagnosticsStore(tmp_path / "preferences.db") as store:
        store._conn.execute(
            "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("alice", "alice@example.com", "Alice", "x" * 32, "now", "now", "now"),
        )
        assert store.notification_preferences("alice") == {
            "inApp": True, "email": True, "mobile": False,
            "criticalPatterns": True, "recommendations": True,
            "validationResults": True, "sourceHealth": True,
            "weeklyDigest": False, "quietHours": True,
            "quietStart": "22:00", "quietEnd": "07:00",
        }
        saved = store.save_notification_preferences("alice", {
            "inApp": False, "email": False, "mobile": True,
            "criticalPatterns": True, "recommendations": False,
            "validationResults": True, "sourceHealth": False,
            "weeklyDigest": True, "quietHours": False,
            "quietStart": "23:30", "quietEnd": "06:15",
        })
        assert saved is not None and saved["mobile"] is True
        assert store.save_notification_preferences("missing", saved) is None
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "UPDATE notification_preferences SET quiet_start='24:00' WHERE user_id='alice'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            store._conn.execute(
                "UPDATE notification_preferences SET in_app=2 WHERE user_id='alice'"
            )
        store._conn.execute("DELETE FROM users WHERE id='alice'")
        assert store._conn.execute("SELECT COUNT(*) FROM notification_preferences").fetchone()[0] == 0


def test_v10_database_upgrades_with_notification_preferences_schema(tmp_path):
    db_path = tmp_path / "v10.db"
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_active_at TEXT NOT NULL
        );
        CREATE TABLE notifications (
            id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            href TEXT NOT NULL,
            is_read INTEGER NOT NULL,
            read_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, id)
        );
        INSERT INTO users VALUES (
            'alice', 'alice@example.com', 'Alice',
            'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', 'now', 'now', 'now'
        );
        INSERT INTO notifications VALUES (
            'notification-1', 'alice', 'PATTERN', 'Pattern', 'Detail',
            '/diagnostics/patterns', 0, NULL, 'now', 'now'
        );
        PRAGMA user_version=10;
        """
    )
    connection.close()

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 11
        assert store._conn.execute(
            "SELECT title FROM notifications WHERE user_id='alice'"
        ).fetchone()["title"] == "Pattern"
        assert store._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notification_preferences'"
        ).fetchone()["name"] == "notification_preferences"

    with DiagnosticsStore(db_path) as store:
        assert store.schema_version == 11
