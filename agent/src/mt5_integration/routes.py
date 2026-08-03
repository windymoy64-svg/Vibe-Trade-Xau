"""FastAPI routes for MT5 Direct Integration & MCP Bridge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.diagnostics.store import DiagnosticsStore
from .service import MTPyBridgeService, MCPTokenService


router = APIRouter(prefix="/mt5", tags=["MT5 Integration"])


class CreateExecutionLogRequest(BaseModel):
    """Payload for manual/auto execution log entry."""
    executionSource: str = Field(min_length=1)  # MANUAL or AUTO_BY_AI
    orderType: str = Field(min_length=1, max_length=32)  # BUY, SELL, etc.
    symbol: str = Field(min_length=1, max_length=32)  # XAUUSD, EURUSD, etc.
    volume: float = Field(gt=0, le=100)  # Lot size
    price: float | None = Field(default=None, gt=0)
    stopLoss: float | None = Field(default=None, gt=0)
    takeProfit: float | None = Field(default=None, gt=0)
    brokerOrderId: str | None = Field(default=None, max_length=64)
    brokerPositionId: str | None = Field(default=None, max_length=64)
    status: str = Field(...)  # PENDING, EXECUTED, CANCELLED, FAILED
    errorCode: int | None = Field(default=None, ge=-10000)
    errorMessage: str | None = Field(default=None, max_length=500)
    timestamp: str = Field(...)  # ISO timestamp
    metadata: dict[str, Any] = Field(default_factory=dict)


class TokenGenerateResponse(BaseModel):
    """MCP token generation response."""
    tokenId: str
    userId: str
    provider: str
    expiresAt: str
    createdAt: str
    isValid: bool


class ConnectionStatusResponse(BaseModel):
    """MT5 connection health summary."""
    userId: str
    terminalConnected: bool
    lastTickTime: str | None
    ticker: dict[str, float] | None  # bid, ask, last
    positionsCount: int
    pendingOrdersCount: int
    latencyMs: int | None
    errorCode: int | None


def register_mt5_routes(app: Any, store: DiagnosticsStore) -> None:
    """Register all MT5/MCP routes with FastAPI app."""
    bridge_service = MTPyBridgeService(store)
    token_service = MCPTokenService(store)

    @app.post("/execution-log", response_model=dict[str, Any])
    async def log_execution(
        request: CreateExecutionLogRequest,
        user_id: str = Depends(lambda: "user-123"),  # Placeholder - use auth in prod
    ) -> dict[str, Any]:
        """Append one execution audit event with source tracking."""
        result = bridge_service.create_execution_log(user_id, {
            "executionSource": request.executionSource,
            "orderType": request.orderType,
            "symbol": request.symbol,
            "volume": request.volume,
            "price": request.price,
            "stopLoss": request.stopLoss,
            "takeProfit": request.takeProfit,
            "brokerOrderId": request.brokerOrderId,
            "brokerPositionId": request.brokerPositionId,
            "status": request.status,
            "errorCode": request.errorCode,
            "errorMessage": request.errorMessage,
            "timestamp": request.timestamp,
            "metadata": request.metadata,
        })
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        return result

    @app.get("/execution-log", response_model=list[dict[str, Any]])
    async def get_execution_logs(
        user_id: str = Depends(lambda: "user-123"),  # Placeholder - use auth in prod
        source: str | None = None,
        status: str | None = None,
        symbol: str | None = None,
        limit: int = Query(100, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        """Query filtered execution logs by source/status/symbol."""
        return bridge_service.get_user_logs(user_id, source=source, status=status, symbol=symbol, limit=limit)

    @app.post("/token/generate", response_model=TokenGenerateResponse)
    async def generate_mcp_token(
        user_id: str = Depends(lambda: "user-123"),  # Placeholder - use auth in prod
        expires_hours: int = Query(24, ge=1, le=720),
    ) -> TokenGenerateResponse:
        """Generate new MCP token for EA/client authentication."""
        token_id, metadata = token_service.generate_token(user_id, expires_hours=expires_hours)
        if not token_id:
            raise HTTPException(status_code=500, detail="Failed to generate token")
        return TokenGenerateResponse(**metadata)

    @app.get("/connection/status", response_model=ConnectionStatusResponse)
    async def get_connection_status(
        user_id: str = Depends(lambda: "user-123"),  # Placeholder - use auth in prod
    ) -> ConnectionStatusResponse:
        """Return current MT5 connection health snapshot."""
        info = bridge_service.get_connection_info(user_id)
        return ConnectionStatusResponse(
            userId=user_id,
            terminalConnected=info.terminal_connected,
            lastTickTime=info.last_tick_time,
            ticker=info.ticker,
            positionsCount=info.positions_count,
            pendingOrdersCount=info.pending_orders_count,
            latency_ms=info.latency_ms,
            error_code=info.error_code,
        )

    @app.get("/live/ohlc/mock", response_model=dict[str, Any])
    async def get_mock_ohlc(
        user_id: str = Depends(lambda: "user-123"),  # Placeholder - use auth in prod
        symbol: str = "XAUUSD",
    ) -> dict[str, Any]:
        """Return mock OHLC tick data for development/testing."""
        bar = await bridge_service.simulate_live_tick(user_id, symbol)
        return {
            "timestamp": bar.timestamp,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "tickVolume": bar.tick_volume,
            "spread": bar.spread,
            "symbol": bar.symbol,
            "timeframe": bar.timeframe,
        }
