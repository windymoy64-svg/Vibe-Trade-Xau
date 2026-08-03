from datetime import datetime, timezone

import pytest

from src.diagnostics.store import DiagnosticsStore
from src.trading.auto_trade import (
    AutoTradeExecutionLogger,
    ExecutionLogEvent,
    ExecutionLogUserNotFoundError,
)


def _event(**overrides):
    return ExecutionLogEvent(**{
        "user_id": "alice", "status": "EXECUTED", "level": "SIGNAL",
        "message": "BUY order filled.",
        "timestamp": datetime(2026, 8, 1, 9, tzinfo=timezone.utc),
        "symbol": "xauusd", "direction": "BUY", "lot_size": 0.05,
        "price": 2389.8, "stop_loss": 2383.8, "take_profit": 2401.8,
        "broker_order_id": "1842", **overrides,
    })


def test_execution_logger_persists_status_price_and_utc_timestamp(tmp_path):
    db_path = tmp_path / "execution.db"
    with DiagnosticsStore(db_path) as store:
        store._conn.execute(
            "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("alice", "alice@example.com", "Alice", "x" * 32, "now", "now", "now"),
        )
        persisted = AutoTradeExecutionLogger(store).record(_event())
        row = store._conn.execute(
            "SELECT * FROM auto_trade_execution_logs WHERE user_id='alice'",
        ).fetchone()

    assert persisted["status"] == "EXECUTED"
    assert row["entry_price"] == 2389.8
    assert row["occurred_at"] == "2026-08-01T09:00:00+00:00"
    assert row["broker_order_id"] == "1842"


def test_execution_logger_publishes_only_after_persistence(tmp_path):
    published = []
    with DiagnosticsStore(tmp_path / "publish.db") as store:
        store._conn.execute(
            "INSERT INTO users (id, email, name, password_hash, created_at, updated_at, last_active_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("alice", "alice@example.com", "Alice", "x" * 32, "now", "now", "now"),
        )
        AutoTradeExecutionLogger(
            store, lambda user_id, event: published.append((user_id, event)),
        ).record(_event())

    assert published[0][0] == "alice"
    assert published[0][1]["status"] == "EXECUTED"


def test_execution_logger_rejects_missing_user_and_invalid_event(tmp_path):
    with DiagnosticsStore(tmp_path / "missing.db") as store:
        with pytest.raises(ExecutionLogUserNotFoundError):
            AutoTradeExecutionLogger(store).record(_event(user_id="missing"))
    with pytest.raises(ValueError, match="timezone-aware"):
        _event(timestamp=datetime(2026, 8, 1, 9))
    with pytest.raises(ValueError, match="positive"):
        _event(price=-1)
