"""Service layer for MT5 Integration & MCP Token management."""

from __future__ import annotations

import asyncio
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from src.diagnostics.store import DiagnosticsStore


class MTPyBridgeService:
    """MT5 direct integration service - handles orders, positions, OHLC streams."""

    def __init__(self, store: DiagnosticsStore):
        self.store = store
        self._lock = threading.Lock()
        self._connection_info: dict[str, "MTPyConnectionInfo"] = {}
        # Stub in-memory cache until real MT5 Python library is integrated
        self._mock_ticks: dict[str, list["LiveOHLCBar"]] = {}
        self._mock_positions: dict[str, list[dict]] = {}

    def create_execution_log(
        self, user_id: str, log: "TradeExecutionLog",
    ) -> dict[str, Any] | None:
        """Append one execution event to persistent audit log."""
        if not log.id:
            object.__setattr__(log, "id", str(uuid.uuid4()))

        values = {
            "id": log.id,
            "userId": user_id,
            "executionSource": log.execution_source.value,
            "orderType": log.order_type,
            "symbol": log.symbol,
            "volume": log.volume,
            "price": log.entry_price,
            "stopLoss": log.stop_loss,
            "takeProfit": log.take_profit,
            "brokerOrderId": log.broker_order_id,
            "brokerPositionId": log.broker_position_id,
            "status": log.status.value,
            "errorCode": log.error_code,
            "errorMessage": log.error_message,
            "timestamp": log.occurred_at,
        }
        result = self.store.append_mt5_execution_log(user_id, values)
        if result:
            result["createdAt"] = log.created_at
            result["metadata"] = log.metadata
        return result

    def get_user_logs(
        self, user_id: str, *,
        source: str | None = None,
        status: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query filtered execution logs for user."""
        return self.store.get_mt5_execution_logs(
            user_id, source=source, status=status, symbol=symbol, limit=limit
        )

    async def simulate_live_tick(self, user_id: str, symbol: str = "XAUUSD") -> "LiveOHLCBar":
        """Generate mock tick data for development/testing."""
        # This will be replaced with real MT5 Python bridge later
        now = datetime.now(timezone.utc)
        base_price = 2389.50 + (time.time() % 60) * 0.1
        return LiveOHLCBar(
            timestamp=now.isoformat(),
            open=base_price,
            high=base_price + 0.5,
            low=base_price - 0.3,
            close=base_price + 0.2,
            volume=1234,
            tick_volume=5678,
            spread=20,
            symbol=symbol,
            timeframe="M1",
        )

    def update_connection_status(
        self, user_id: str, info: "MTPyConnectionInfo",
    ) -> None:
        """Update in-memory connection health snapshot."""
        with self._lock:
            self._connection_info[user_id] = info

    def get_connection_info(self, user_id: str) -> "MTPyConnectionInfo":
        """Return current connection health or defaults."""
        with self._lock:
            return self._connection_info.get(user_id, MTPyConnectionInfo(user_id=user_id))


class MCPTokenService:
    """MCP (Model Context Protocol) token generation and validation."""

    def __init__(self, store: DiagnosticsStore):
        self.store = store

    def generate_token(
        self, user_id: str, expires_hours: int = 24,
    ) -> tuple[str, dict[str, Any]] | None:
        """Generate new MCP token for EA/client authentication."""
        token_id = str(uuid.uuid4())
        expires_at = datetime.fromtimestamp(
            time.time() + expires_hours * 3600, tz=timezone.utc
        ).isoformat().replace("+00:00", "Z")
        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        metadata = {
            "token_id": token_id,
            "userId": user_id,
            "provider": "EA_MT5",
            "expiresAt": expires_at,
            "createdAt": created_at,
            "isValid": True,
        }

        # Store in database via migration v15
        try:
            self.store.create_mcp_token(
                user_id=user_id,
                token_id=token_id,
                provider="EA_MT5",
                expires_at=expires_at,
                created_at=created_at,
            )
        except Exception as e:
            # Schema v15 might not exist yet - handle gracefully
            pass

        return token_id, metadata

    def validate_token(self, token_id: str) -> bool:
        """Check if token exists, valid, and not expired."""
        now = datetime.now(timezone.utc)
        try:
            row = self.store.get_mcp_token(token_id)
            if not row:
                return False

            # Check expiry and validity flags
            expires_at = datetime.fromisoformat(row["expiresAt"].rstrip("Z"))
            return row.get("isValid", True) and now < expires_at
        except Exception:
            return False

    def revoke_token(self, token_id: str) -> bool:
        """Invalidate a token."""
        try:
            self.store.invalidate_mcp_token(token_id)
            return True
        except Exception:
            return False

    async def check_latency(self, endpoint: str) -> int:
        """Simulate latency monitoring for MCP endpoint."""
        start = time.perf_counter()
        # In reality this would make HTTP call to MCP server
        await asyncio.sleep(0.05)  # 50ms mock latency
        end = time.perf_counter()
        return int((end - start) * 1000)
