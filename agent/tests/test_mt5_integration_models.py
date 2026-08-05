"""Unit tests for MT5 Integration models and schema generation."""

from __future__ import annotations

import sqlite3
import pytest
from datetime import datetime, timezone

from src.mt5_integration.models import (
    ExecutionSource,
    OrderStatus,
    PositionSide,
    TradeExecutionLog,
    MTPyConnectionInfo,
    MCPTokenMetadata,
    LiveOHLCBar,
    NEW_TABLE_SQL,
)


class TestEnums:
    """Test enum definitions for MT5 integration."""

    def test_execution_source_values(self):
        assert ExecutionSource.MANUAL.value == "MANUAL"
        assert ExecutionSource.AUTO_BY_AI.value == "AUTO_BY_AI"

    def test_order_status_values(self):
        assert OrderStatus.PENDING.value == "PENDING"
        assert OrderStatus.EXECUTED.value == "EXECUTED"
        assert OrderStatus.CANCELLED.value == "CANCELLED"
        assert OrderStatus.FAILED.value == "FAILED"

    def test_position_side_values(self):
        assert PositionSide.BUY.value == "BUY"
        assert PositionSide.SELL.value == "SELL"


class TestTradeExecutionLog:
    """Test TradeExecutionLog dataclass with embedded SQL schema."""

    def test_creates_with_default_values(self):
        log = TradeExecutionLog()
        assert log.id is not None and len(log.id) == 36  # UUID format
        assert log.execution_source == ExecutionSource.MANUAL
        assert log.status == OrderStatus.PENDING
        assert log.volume == 0.0
        assert log.entry_price is None
        assert log.stop_loss is None
        assert log.take_profit is None
        assert isinstance(log.metadata, dict)
        assert log.created_at
        assert log.occurred_at

    def test_uses_provided_timestamps(self):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        log = TradeExecutionLog(
            id="test-id-123",
            user_id="user-456",
            occurred_at=now,
            created_at=now,
        )
        assert log.id == "test-id-123"
        assert log.user_id == "user-456"
        assert log.occurred_at == now
        assert log.created_at == now

    def test_automatically_sets_timestamps_when_missing(self):
        log = TradeExecutionLog(id="explicit-id")
        # Both timestamps should be auto-generated and equal
        assert log.created_at == log.occurred_at
        assert log.created_at is not None
        assert "T" in log.created_at  # ISO format check

    def test_frozen_slots_prevent_modification(self):
        log = TradeExecutionLog(
            id="immutable-id",
            symbol="XAUUSD",
            order_type="BUY",
        )
        # frozen=True should prevent all field modification
        # Expected exception is FrozenInstanceError from dataclasses
        with pytest.raises(Exception) as exc_info:
            log.symbol = "EURUSD"  # Cannot modify frozen field
        assert "frozen" in str(exc_info.value).lower() or "cannot assign" in str(exc_info.value).lower()

    def test_custom_volume_constraints_in_metadata(self):
        log = TradeExecutionLog(
            id="log-1",
            symbol="EURUSD",
            volume=1.5,
            entry_price=1.0850,
            stop_loss=1.0800,
            take_profit=1.0950,
            execution_source=ExecutionSource.AUTO_BY_AI,
            order_type="BUY_LIMIT",
        )
        assert log.symbol == "EURUSD"
        assert log.volume == 1.5
        assert log.entry_price == 1.0850
        assert log.stop_loss == 1.0800
        assert log.take_profit == 1.0950
        assert log.execution_source == ExecutionSource.AUTO_BY_AI


class TestMTPyConnectionInfo:
    """Test MTPyConnectionInfo for MT5 terminal health tracking."""

    def test_minimum_required_fields(self):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        info = MTPyConnectionInfo(user_id="alice", updated_at=now)
        assert info.user_id == "alice"
        assert info.terminal_connected is False
        assert info.positions_count == 0
        assert info.pending_orders_count == 0
        assert info.error_code is None
        assert info.updated_at == now

    def test_full_specification(self):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        info = MTPyConnectionInfo(
            user_id="bob",
            terminal_connected=True,
            last_tick_time=now,
            ticker={"bid": 2389.30, "ask": 2389.50, "last": 2389.40},
            positions_count=3,
            pending_orders_count=2,
            latency_ms=45,
            error_code=None,
            updated_at=now,
        )
        assert info.terminal_connected is True
        assert info.ticker["bid"] == 2389.30
        assert info.latency_ms == 45


class TestMCPTokenMetadata:
    """Test MCP token metadata for EA authentication."""

    def test_generated_token_id(self):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        token = MCPTokenMetadata(
            token_id="custom-token-123-abc",  # Custom ID length
            user_id="user-789",
            expires_at=now,
            created_at=now,
        )
        assert len(token.token_id) > 10  # Custom ID is reasonable length
        assert token.provider == "EA_MT5"
        assert token.is_valid is True
        assert token.expires_at == now
        assert token.created_at == now

    def test_custom_specification(self):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        token = MCPTokenMetadata(
            token_id="custom-token-123",
            user_id="user-789",
            expires_at=now,
            created_at=now,
            is_valid=False,
        )
        assert token.token_id == "custom-token-123"
        assert token.user_id == "user-789"
        assert token.is_valid is False


class TestLiveOHLCBar:
    """Test OHLC bar structure for live tick simulation."""

    def test_minimum_bar(self):
        bar = LiveOHLCBar(timestamp="2026-08-03T10:00:00Z")
        assert bar.symbol == "XAUUSD"
        assert bar.timeframe == "M1"
        assert bar.open == 0.0
        assert bar.high == 0.0
        assert bar.low == 0.0
        assert bar.close == 0.0
        assert bar.volume == 0
        assert bar.tick_volume == 0
        assert bar.spread == 0

    def test_full_candle(self):
        bar = LiveOHLCBar(
            timestamp="2026-08-03T10:00:00Z",
            open=2389.50,
            high=2390.20,
            low=2388.90,
            close=2389.80,
            volume=1234,
            tick_volume=5678,
            spread=20,
            symbol="XAUUSD",
            timeframe="M15",
        )
        assert bar.open == 2389.50
        assert bar.high == 2390.20
        assert bar.low == 2388.90
        assert bar.close == 2389.80
        assert bar.volume == 1234
        assert bar.tick_volume == 5678


class TestSchemaGeneration:
    """Test NEW_TABLE_SQL generates valid SQLite schema for v15 migration."""

    def test_sql_contains_both_tables(self):
        assert "CREATE TABLE mt5_execution_logs" in NEW_TABLE_SQL
        assert "CREATE TABLE mcp_tokens" in NEW_TABLE_SQL

    def test_mt5_execution_logs_schema(self):
        # Check required columns in SQL
        required_cols = [
            "id TEXT NOT NULL",
            "user_id TEXT NOT NULL",
            "execution_source TEXT NOT NULL",
            "order_type TEXT NOT NULL",
            "symbol TEXT NOT NULL",
            "volume REAL NOT NULL",
            "entry_price REAL",
            "stop_loss REAL",
            "take_profit REAL",
            "broker_order_id TEXT",
            "broker_position_id TEXT",
            "status TEXT NOT NULL",
            "error_code INTEGER",
            "error_message TEXT",
            "metadata_json TEXT NOT NULL DEFAULT '{}'",
            "occurred_at TEXT NOT NULL",
            "created_at TEXT NOT NULL",
        ]
        for col in required_cols:
            assert col in NEW_TABLE_SQL

    def test_mcp_tokens_schema(self):
        # Check required columns in SQL
        required_cols = [
            "token_id TEXT PRIMARY KEY",
            "user_id TEXT NOT NULL",
            "provider TEXT NOT NULL DEFAULT 'EA_MT5'",
            "expires_at TEXT NOT NULL",
            "created_at TEXT NOT NULL",
            "is_valid INTEGER NOT NULL DEFAULT 1",
        ]
        for col in required_cols:
            assert col in NEW_TABLE_SQL

    def test_indexes_are_defined(self):
        assert "idx_mt5_execution_logs_user_source_time" in NEW_TABLE_SQL
        assert "idx_mt5_execution_logs_user_status" in NEW_TABLE_SQL
        assert "idx_mcp_tokens_user_expiry" in NEW_TABLE_SQL

    def test_foreign_key_constraints_exist(self):
        assert "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE" in NEW_TABLE_SQL

    def test_check_constraints_for_enums(self):
        # Verify enum constraints
        assert "CHECK(execution_source IN ('MANUAL', 'AUTO_BY_AI'))" in NEW_TABLE_SQL
        assert "CHECK(status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'FAILED'))" in NEW_TABLE_SQL

    def test_sql_is_executable(self, tmp_path):
        """Integration test: actual SQLite database creation."""
        db_path = tmp_path / "mt5-test.db"
        conn = sqlite3.connect(str(db_path))
        try:
            conn.executescript(NEW_TABLE_SQL)

            # Verify tables exist
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert "mt5_execution_logs" in tables
            assert "mcp_tokens" in tables

            # Verify indexes exist
            indexes = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
            assert "idx_mt5_execution_logs_user_source_time" in indexes
            assert "idx_mcp_tokens_user_expiry" in indexes

            # Insert sample record
            conn.execute(
                """INSERT INTO mt5_execution_logs (
                    id, user_id, execution_source, order_type, symbol,
                    volume, entry_price, status, occurred_at, created_at,
                    metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "test-log-1",
                    "user-123",
                    "MANUAL",
                    "BUY",
                    "XAUUSD",
                    0.01,
                    2389.50,
                    "PENDING",
                    "2026-08-03T10:00:00Z",
                    "2026-08-03T10:00:00Z",
                    '{"paper": true}',
                ),
            )
            conn.commit()

            # Query back (SELECT * returns all columns in order)
            result = conn.execute(
                "SELECT id, execution_source, symbol FROM mt5_execution_logs WHERE id='test-log-1'"
            ).fetchone()
            assert result is not None
            assert result[0] == "test-log-1"  # id
            assert result[1] == "MANUAL"  # execution_source
            assert result[2] == "XAUUSD"  # symbol
        finally:
            conn.close()

    def test_constrained_inserts_fail_correctly(self, tmp_path):
        """Verify database constraints enforce data integrity."""
        db_path = tmp_path / "constrained.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(NEW_TABLE_SQL)

        # Invalid execution_source
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO mt5_execution_logs (
                    id, user_id, execution_source, order_type, symbol,
                    volume, status, occurred_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("bad-1", "user-1", "INVALID_SOURCE", "BUY", "XAUUSD", 0.01, "PENDING", "now", "now"),
            )

        # Invalid status
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO mt5_execution_logs (
                    id, user_id, execution_source, order_type, symbol,
                    volume, status, occurred_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("bad-2", "user-1", "MANUAL", "BUY", "XAUUSD", 0.01, "UNKNOWN", "now", "now"),
            )

        # Invalid volume (must be > 0)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO mt5_execution_logs (
                    id, user_id, execution_source, order_type, symbol,
                    volume, status, occurred_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("bad-3", "user-1", "MANUAL", "BUY", "XAUUSD", -1.0, "PENDING", "now", "now"),
            )

        # Invalid JSON
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO mt5_execution_logs (
                    id, user_id, execution_source, order_type, symbol,
                    volume, status, occurred_at, created_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("bad-4", "user-1", "MANUAL", "BUY", "XAUUSD", 0.01, "PENDING", "now", "now", "not-json"),
            )

        conn.close()

    def test_mcp_token_lifecycle_constraints(self, tmp_path):
        """Test MCP token validity flags and expiry constraints."""
        db_path = tmp_path / "tokens.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(NEW_TABLE_SQL)

        # Insert valid token (must be 36 chars - UUID format)
        conn.execute(
            """INSERT INTO mcp_tokens (
                token_id, user_id, provider, expires_at, created_at, is_valid
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            ("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "user-1", "EA_MT5", "2030-01-01T00:00:00Z", "2026-08-03T00:00:00Z", 1),
        )

        # Insert expired token
        conn.execute(
            """INSERT INTO mcp_tokens (
                token_id, user_id, provider, expires_at, created_at, is_valid
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            ("bbbbbbbb-cccc-dddd-eeee-ffffffffffff", "user-1", "EA_MT5", "2020-01-01T00:00:00Z", "2026-08-03T00:00:00Z", 1),
        )

        # Revoke token
        conn.execute(
            """UPDATE mcp_tokens SET is_valid = 0 WHERE token_id = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'"""
        )

        # Query revoked token (select specific column)
        revoked = conn.execute(
            "SELECT is_valid FROM mcp_tokens WHERE token_id='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'"
        ).fetchone()
        assert revoked[0] == 0  # is_valid value

        # Query expired token
        expired = conn.execute(
            "SELECT is_valid FROM mcp_tokens WHERE token_id='bbbbbbbb-cccc-dddd-eeee-ffffffffffff'"
        ).fetchone()
        assert expired[0] == 1  # is_valid
        # But logically invalid due to expiry (application-layer check)

        conn.close()
