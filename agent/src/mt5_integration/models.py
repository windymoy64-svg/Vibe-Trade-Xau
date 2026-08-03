"""Data models for MT5 Integration & MCP Bridge."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ExecutionSource(Enum):
    """Track whether trade came from manual or auto-execution."""
    MANUAL = "MANUAL"
    AUTO_BY_AI = "AUTO_BY_AI"


class OrderStatus(Enum):
    """Order lifecycle states in MT5."""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class PositionSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class TradeExecutionLog:
    """Immutable audit log for each order/position event with source tracking."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str | None = None
    execution_source: ExecutionSource = ExecutionSource.MANUAL
    order_type: str = ""  # BUY, SELL, BUY_LIMIT, etc.
    symbol: str = ""
    volume: float = 0.0
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    broker_order_id: str | None = None
    broker_position_id: str | None = None
    status: OrderStatus = OrderStatus.PENDING
    error_code: int | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: str = ""  # ISO timestamp when event happened
    created_at: str = ""  # When we logged it

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        if not self.occurred_at:
            object.__setattr__(self, "occurred_at", self.created_at)


@dataclass(frozen=True, slots=True)
class MTPyConnectionInfo:
    """MT5 terminal connection health and metadata."""
    user_id: str
    terminal_connected: bool = False
    last_tick_time: str | None = None
    ticker: dict[str, float] | None = None  # bid, ask, last
    positions_count: int = 0
    pending_orders_count: int = 0
    latency_ms: int | None = None
    error_code: int | None = None
    updated_at: str = ""


@dataclass(frozen=True, slots=True)
class MCPTokenMetadata:
    """Generated token for EA/MCP client authentication."""
    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    provider: str = "EA_MT5"
    expires_at: str = ""  # ISO timestamp
    created_at: str = ""  # ISO timestamp
    is_valid: bool = True


@dataclass(frozen=True, slots=True)
class LiveOHLCBar:
    """Single OHLC bar with tick stream augmentation."""
    timestamp: str  # ISO timestamp
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    tick_volume: int = 0
    spread: int = 0
    symbol: str = "XAUUSD"
    timeframe: str = "M1"


# Schema definition for migration v15
NEW_TABLE_SQL = """
CREATE TABLE mt5_execution_logs (
    id TEXT NOT NULL CHECK(length(trim(id)) BETWEEN 1 AND 128),
    user_id TEXT NOT NULL,
    execution_source TEXT NOT NULL CHECK(execution_source IN ('MANUAL', 'AUTO_BY_AI')),
    order_type TEXT NOT NULL CHECK(length(order_type) BETWEEN 1 AND 32),
    symbol TEXT NOT NULL CHECK(length(symbol) BETWEEN 1 AND 32),
    volume REAL NOT NULL CHECK(volume > 0 AND volume <= 100),
    entry_price REAL CHECK(entry_price IS NULL OR entry_price > 0),
    stop_loss REAL CHECK(stop_loss IS NULL OR stop_loss > 0),
    take_profit REAL CHECK(take_profit IS NULL OR take_profit > 0),
    broker_order_id TEXT CHECK(broker_order_id IS NULL OR length(broker_order_id) <= 64),
    broker_position_id TEXT CHECK(broker_position_id IS NULL OR length(broker_position_id) <= 64),
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'FAILED')),
    error_code INTEGER CHECK(error_code IS NULL OR error_code >= -10000),
    error_message TEXT CHECK(error_message IS NULL OR length(error_message) <= 500),
    metadata_json TEXT NOT NULL DEFAULT '{}'
        CHECK(json_valid(metadata_json) AND json_type(metadata_json) = 'object'),
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id, id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_mt5_execution_logs_user_source_time
    ON mt5_execution_logs(user_id, execution_source, occurred_at DESC, id);

CREATE INDEX idx_mt5_execution_logs_user_status
    ON mt5_execution_logs(user_id, status, created_at DESC);

CREATE TABLE mcp_tokens (
    token_id TEXT PRIMARY KEY CHECK(length(token_id) = 36),
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'EA_MT5'
        CHECK(length(provider) BETWEEN 1 AND 64),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_valid INTEGER NOT NULL DEFAULT 1 CHECK(is_valid IN (0, 1)),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_mcp_tokens_user_expiry
    ON mcp_tokens(user_id, expires_at ASC);
"""
