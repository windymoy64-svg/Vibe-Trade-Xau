"""FastAPI routes for MT5 Direct Integration & MCP Bridge."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from src.api.security import require_local_or_auth
from src.diagnostics.store import DiagnosticsStore
from .service import MTPyBridgeService, MCPTokenService


router = APIRouter(prefix="/mt5", tags=["MT5 Integration"])


class CreateExecutionLogRequest(BaseModel):
    """Payload for manual/auto execution log entry."""
    executionSource: str = Field(..., min_length=1)  # MANUAL or AUTO_BY_AI
    orderType: str = Field(..., min_length=1, max_length=32)  # BUY, SELL, etc.
    symbol: str = Field(..., min_length=1, max_length=32)  # XAUUSD, EURUSD, etc.
    volume: float = Field(..., gt=0, le=100)  # Lot size
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


class MT5ConfigurationRequest(BaseModel):
    login: int = Field(gt=0)
    password: str = Field(default="", max_length=256)
    server: str = Field(min_length=1, max_length=128)
    terminalPath: str = Field(default="", max_length=1024)
    profile: str = Field(pattern=r"^(paper|live-readonly|live)$")
    symbolSuffix: str = Field(default="", max_length=16)
    timeout: float = Field(default=15, ge=1, le=60)
    maxOrderVolume: float = Field(default=1, gt=0, le=100)
    maxOrderNotionalUsd: float = Field(default=10_000, gt=0, le=100_000_000)

    @field_validator("password")
    @classmethod
    def reject_control_characters(cls, value: str) -> str:
        if any(not character.isprintable() for character in value):
            raise ValueError("password contains control characters")
        return value


class MT5ConfigurationResponse(BaseModel):
    loginMasked: str
    login: int
    passwordConfigured: bool
    server: str
    terminalPath: str
    profile: str
    symbolSuffix: str
    timeout: float
    maxOrderVolume: float
    maxOrderNotionalUsd: float
    configPath: str


def register_mt5_routes(app: Any, store: DiagnosticsStore) -> None:
    """Register all MT5/MCP routes with FastAPI app."""
    bridge_service = MTPyBridgeService(store)
    token_service = MCPTokenService(store)

    def ensure_local_user() -> None:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with store._conn:
            store._conn.execute(
                """INSERT OR IGNORE INTO users (
                    id, email, name, password_hash, created_at, updated_at, last_active_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("user-123", "local-terminal@localhost", "Local MT5 Terminal", "x" * 32, now, now, now),
            )

    def configuration_response(config: Any) -> MT5ConfigurationResponse:
        from src.trading.connectors.mt5.sdk import config_path
        login_text = str(config.login) if config.login else ""
        return MT5ConfigurationResponse(
            loginMasked=(login_text[:2] + "***" + login_text[-2:]) if len(login_text) > 4 else ("***" if login_text else ""),
            login=config.login, passwordConfigured=bool(config.password), server=config.server,
            terminalPath=config.terminal_path, profile=config.profile, symbolSuffix=config.symbol_suffix,
            timeout=config.timeout, maxOrderVolume=config.max_order_volume,
            maxOrderNotionalUsd=config.max_order_notional_usd, configPath=str(config_path()),
        )

    @app.get("/mt5/configuration", response_model=MT5ConfigurationResponse, dependencies=[Depends(require_local_or_auth)])
    async def get_mt5_configuration() -> MT5ConfigurationResponse:
        from src.trading.connectors.mt5.sdk import load_config
        return configuration_response(load_config())

    @app.put("/mt5/configuration", response_model=MT5ConfigurationResponse, dependencies=[Depends(require_local_or_auth)])
    async def save_mt5_configuration(payload: MT5ConfigurationRequest) -> MT5ConfigurationResponse:
        from src.trading.connectors.mt5.sdk import MT5Config, load_config, save_config
        current = load_config()
        config = MT5Config.from_mapping({
            "login": payload.login, "password": payload.password or current.password,
            "server": payload.server, "terminal_path": payload.terminalPath,
            "profile": payload.profile, "symbol_suffix": payload.symbolSuffix,
            "timeout": payload.timeout, "max_order_volume": payload.maxOrderVolume,
            "max_order_notional_usd": payload.maxOrderNotionalUsd,
            "deviation_points": current.deviation_points, "readonly": payload.profile != "live",
        })
        save_config(config)
        ensure_local_user()
        return configuration_response(config)

    @app.post("/mt5/execution-log", include_in_schema=False)
    @app.post("/execution-log")
    async def log_execution(
        request: CreateExecutionLogRequest,
        user_id: str = "user-123",  # Placeholder - use auth in prod
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

    @app.get("/mt5/execution-log", include_in_schema=False)
    @app.get("/execution-log")
    async def get_execution_logs(
        user_id: str = "user-123",  # Placeholder - use auth in prod
        source: str | None = None,
        status: str | None = None,
        symbol: str | None = None,
        limit: int = Query(100, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        """Query filtered execution logs by source/status/symbol."""
        return bridge_service.get_user_logs(user_id, source=source, status=status, symbol=symbol, limit=limit)

    @app.post("/mt5/token/generate")
    @app.post("/token/generate", include_in_schema=False)
    async def generate_mcp_token(
        user_id: str = "user-123",  # Placeholder - use auth in prod
        expires_hours: int = Query(24, ge=1, le=720),
    ) -> TokenGenerateResponse:
        """Generate new MCP token for EA/client authentication."""
        if user_id == "user-123":
            ensure_local_user()
        token_id, metadata = token_service.generate_token(user_id, expires_hours=expires_hours)
        if not token_id:
            raise HTTPException(status_code=500, detail="Failed to generate token")
        return TokenGenerateResponse(
            tokenId=metadata["token_id"],
            userId=metadata["userId"],
            provider=metadata["provider"],
            expiresAt=metadata["expiresAt"],
            createdAt=metadata["createdAt"],
            isValid=metadata["isValid"],
        )

    @app.get("/mt5/token/active", response_model=TokenGenerateResponse | None)
    @app.get("/token/active", response_model=TokenGenerateResponse | None, include_in_schema=False)
    async def get_active_mcp_token(
        user_id: str = "user-123",
    ) -> TokenGenerateResponse | None:
        """Return active MCP token metadata so clients can restore token state."""
        if user_id == "user-123":
            ensure_local_user()
        metadata = token_service.active_token(user_id)
        return TokenGenerateResponse(**metadata) if metadata else None

    @app.get("/mt5/connection/status")
    @app.get("/connection/status", include_in_schema=False)
    async def get_connection_status(
        user_id: str = "user-123",  # Placeholder - use auth in prod
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
            latencyMs=info.latency_ms,
            errorCode=info.error_code,
        )

    @app.get("/mt5/live/ohlc/mock")
    @app.get("/live/ohlc/mock", include_in_schema=False)
    async def get_mock_ohlc(
        user_id: str = "user-123",  # Placeholder - use auth in prod
        symbol: str = "XAUUSD",
    ) -> dict[str, Any]:
        """Return mock OHLC tick data for development/testing."""
        bar = bridge_service.simulate_live_tick(user_id, symbol)
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

    @app.get("/mt5/live/snapshot")
    async def get_live_snapshot(
        user_id: str = "user-123",
        symbol: str = Query("XAUUSD", min_length=1, max_length=32),
        timeframe: str = Query("M30", pattern=r"^(M1|M5|M15|M30|H1|H4|D1)$"),
        limit: int = Query(80, ge=20, le=500),
    ) -> dict[str, Any]:
        """Return real read-only market/account data from the local MT5 terminal."""
        snapshot = bridge_service.live_snapshot(user_id, symbol.strip().upper(), timeframe, limit)
        if snapshot.get("status") != "ok":
            raise HTTPException(status_code=503, detail=snapshot)
        return snapshot

    @app.delete("/mt5/token/{token_id}", status_code=204)
    async def revoke_mcp_token(token_id: str) -> None:
        """Revoke one EA/MCP bridge token."""
        if not token_service.revoke_token(token_id):
            raise HTTPException(status_code=404, detail="MCP token not found")

