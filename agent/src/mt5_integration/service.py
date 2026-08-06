"""Service layer for MT5 Integration & MCP Token management."""

from __future__ import annotations

import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from src.diagnostics.store import DiagnosticsStore
from .models import MTPyConnectionInfo, LiveOHLCBar, TradeExecutionLog


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
        self, user_id: str, log: "TradeExecutionLog | dict[str, Any]",
    ) -> dict[str, Any] | None:
        """Append one execution event to persistent audit log."""
        if isinstance(log, dict):
            log_data = log
        else:
            # Convert TradeExecutionLog dataclass to dict
            log_data = {
                "executionSource": log.execution_source.value if hasattr(log.execution_source, 'value') else log.execution_source,
                "orderType": log.order_type or "BUY",
                "symbol": log.symbol or "XAUUSD",
                "volume": log.volume or 0.01,
                "price": log.entry_price,
                "stopLoss": log.stop_loss,
                "takeProfit": log.take_profit,
                "brokerOrderId": log.broker_order_id,
                "brokerPositionId": log.broker_position_id,
                "status": log.status.value if hasattr(log.status, 'value') else log.status,
                "errorCode": log.error_code,
                "errorMessage": log.error_message,
                "timestamp": log.occurred_at or datetime.now(timezone.utc).isoformat(),
                "metadata": log.metadata or {},
            }

        values = {
            "executionSource": log_data.get("executionSource", "MANUAL"),
            "orderType": log_data.get("orderType", "BUY"),
            "symbol": log_data.get("symbol", "XAUUSD"),
            "volume": log_data.get("volume") or 0.01,
            "price": log_data.get("price"),
            "stopLoss": log_data.get("stopLoss"),
            "takeProfit": log_data.get("takeProfit"),
            "brokerOrderId": log_data.get("brokerOrderId"),
            "brokerPositionId": log_data.get("brokerPositionId"),
            "status": log_data.get("status", "PENDING"),
            "errorCode": log_data.get("errorCode"),
            "errorMessage": log_data.get("errorMessage"),
            "timestamp": log_data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "metadata": log_data.get("metadata") or {},
        }
        result = self.store.append_mt5_execution_log(user_id, values)
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

    def simulate_live_tick(self, user_id: str, symbol: str = "XAUUSD") -> LiveOHLCBar:
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

    def live_snapshot(self, user_id: str, symbol: str, timeframe: str, limit: int) -> dict[str, Any]:
        """Read a fail-closed market/account snapshot from the local MT5 terminal."""
        from src.trading.connectors.mt5.sdk import (
            check_status, get_account_snapshot, get_historical_bars,
            get_open_orders, get_positions, get_quote,
        )

        period = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m", "H1": "1h", "H4": "4h", "D1": "1d"}.get(timeframe.upper(), "30m")
        status = check_status()
        if status.get("status") != "ok":
            return {"status": "error", "connected": False, "error": status.get("error", "MT5 unavailable"), "sdk": status.get("sdk"), "config": status.get("config")}
        account = get_account_snapshot()
        quote = get_quote(symbol)
        positions = get_positions()
        orders = get_open_orders(include_executions=True)
        bars = get_historical_bars(symbol, period=period, limit=limit)
        errors = [payload.get("error") for payload in (account, quote, positions, orders, bars) if payload.get("status") != "ok"]
        if errors:
            return {"status": "error", "connected": False, "error": "; ".join(str(item) for item in errors)}
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        quote_data = quote.get("quote") or {}
        self.update_connection_status(user_id, MTPyConnectionInfo(
            user_id=user_id, terminal_connected=True, last_tick_time=str(quote_data.get("time") or now),
            ticker={key: float(value) for key, value in quote_data.items() if key in {"bid", "ask", "last"} and value is not None},
            positions_count=len(positions.get("positions") or []), pending_orders_count=len(orders.get("open_orders") or []),
            latency_ms=0, updated_at=now,
        ))
        return {
            "status": "ok", "connected": True, "capturedAt": now,
            "account": account.get("account"), "quote": quote_data,
            "symbol": quote.get("resolved_symbol") or symbol, "timeframe": timeframe.upper(),
            "bars": bars.get("bars") or [], "positions": positions.get("positions") or [],
            "orders": orders.get("open_orders") or [], "executions": orders.get("executions") or [],
        }


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

            # Check expiry and validity flags.
            # Expiry is stored as UTC ISO-8601 with "Z" suffix; reattach tzinfo
            # so comparison with timezone-aware `now` does not raise TypeError.
            expires_at = datetime.fromisoformat(
                row["expiresAt"].rstrip("Z")
            ).replace(tzinfo=timezone.utc)
            return row.get("isValid", True) and now < expires_at
        except Exception:
            return False

    def active_token(self, user_id: str) -> dict[str, Any] | None:
        """Return the latest active token metadata without exposing a secret."""
        return self.store.get_active_mcp_token(user_id, provider="EA_MT5")

    def revoke_token(self, token_id: str) -> bool:
        """Invalidate a token. Returns True if token was found and revoked."""
        try:
            result = self.store.invalidate_mcp_token(token_id)
            return result  # store returns True only if rowcount > 0
        except Exception:
            return False

    def check_latency(self, endpoint: str) -> int:
        """Simulate latency monitoring for MCP endpoint."""
        start = time.perf_counter()
        # In reality this would make HTTP call to MCP server
        end = time.perf_counter()
        return int((end - start) * 1000)
