"""REST and WebSocket delivery for auto-trade execution status changes."""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import Depends, HTTPException, Path, Query, Response, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field, field_validator

from src.api.security import (
    _configured_api_key,
    _consume_sse_ticket,
    _is_local_client,
    require_local_or_auth,
)
from src.diagnostics.store import DiagnosticsStore, EncryptedApiCredentialExistsError
from src.trading.auto_trade import (
    BrokerCredentialEncryptionService,
    CredentialEncryptionConfigurationError,
)

ExecutionStatus = Literal["MONITORING", "PENDING", "EXECUTED", "REJECTED", "CLOSED", "FAILED"]


@dataclass(frozen=True, slots=True)
class ExecutionStatusEvent:
    user_id: str
    execution_id: str
    status: ExecutionStatus
    message: str
    broker_order_id: str | None
    updated_at: str


class ExecutionStatusResponse(BaseModel):
    executionId: str
    status: ExecutionStatus
    message: str
    brokerOrderId: str | None
    updatedAt: str


class RobotControls(BaseModel):
    enabled: bool
    lotSize: float = Field(ge=0.01, le=1, allow_inf_nan=False)
    stopLossPips: float = Field(ge=5, le=250, allow_inf_nan=False)
    takeProfitPips: float = Field(ge=10, le=500, allow_inf_nan=False)


class AutoTradeConfigurationValues(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=16)
    strategy: str = Field(min_length=1, max_length=160)
    riskPerTrade: float = Field(ge=0.01, le=5, allow_inf_nan=False)
    dailyLossLimit: float = Field(ge=0.1, le=20, allow_inf_nan=False)
    paperMode: bool
    robotControls: RobotControls

    @field_validator("symbol", "timeframe", "strategy")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized


class CreateAutoTradeConfigurationRequest(AutoTradeConfigurationValues):
    userId: str = Field(min_length=1, max_length=128)

    @field_validator("userId")
    @classmethod
    def strip_user_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("userId must not be blank")
        return normalized


class AutoTradeConfigurationResponse(AutoTradeConfigurationValues):
    id: str
    userId: str
    createdAt: str
    updatedAt: str


class BrokerCredentialValues(BaseModel):
    apiKey: str = Field(min_length=8, max_length=4096)

    @field_validator("apiKey")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        if value != value.strip() or any(
            character.isspace() or not character.isprintable() for character in value
        ):
            raise ValueError("apiKey must not contain whitespace or control characters")
        ascii_alphanumeric = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        if any(character not in ascii_alphanumeric for character in value[-4:]):
            raise ValueError("apiKey must end with four ASCII letters or digits")
        return value


class CreateBrokerCredentialRequest(BrokerCredentialValues):
    userId: str = Field(min_length=1, max_length=128)
    provider: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
    )


class BrokerCredentialResponse(BaseModel):
    provider: str
    lastFour: str
    keyVersion: int
    createdAt: str
    updatedAt: str


class AutoTradeExecutionLogResponse(BaseModel):
    id: str
    level: Literal["INFO", "SIGNAL", "RISK", "ERROR"]
    status: ExecutionStatus
    message: str
    symbol: str | None
    direction: Literal["BUY", "SELL"] | None
    strategyId: str | None
    lotSize: float | None
    price: float | None
    stopLoss: float | None
    takeProfit: float | None
    brokerOrderId: str | None
    errorCode: str | None
    timestamp: str


def _encryption_service() -> BrokerCredentialEncryptionService:
    try:
        return BrokerCredentialEncryptionService.from_environment()
    except CredentialEncryptionConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def _encrypted_values(
    payload: BrokerCredentialValues, user_id: str, provider: str,
) -> tuple[bytes, bytes, str]:
    encrypted = _encryption_service().encrypt(
        payload.apiKey, user_id=user_id, provider=provider,
    )
    return encrypted.ciphertext, encrypted.nonce, payload.apiKey[-4:]


class ExecutionStatusRegistry:
    def __init__(self, *, maximum_events: int = 500, subscriber_queue_size: int = 50) -> None:
        self.maximum_events = maximum_events
        self.subscriber_queue_size = subscriber_queue_size
        self._events: dict[tuple[str, str], ExecutionStatusEvent] = {}
        self._order: list[tuple[str, str]] = []
        self._subscribers: dict[
            str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[ExecutionStatusEvent]]]
        ] = {}
        self._lock = threading.RLock()

    async def publish(
        self,
        user_id: str,
        execution_id: str,
        status: ExecutionStatus,
        message: str,
        *,
        broker_order_id: str | None = None,
    ) -> ExecutionStatusEvent:
        normalized_user = user_id.strip()
        normalized_id = execution_id.strip()
        normalized_message = message.strip()
        if not normalized_user or not normalized_id or not normalized_message:
            raise ValueError("user, execution ID, and message are required")
        event = ExecutionStatusEvent(
            normalized_user,
            normalized_id,
            status,
            normalized_message,
            broker_order_id,
            datetime.now(timezone.utc).isoformat(),
        )
        key = (normalized_user, normalized_id)
        with self._lock:
            if key not in self._events:
                self._order.append(key)
            self._events[key] = event
            while len(self._order) > self.maximum_events:
                self._events.pop(self._order.pop(0), None)
            subscribers = tuple(self._subscribers.get(normalized_user, ()))
        for loop, queue in subscribers:
            loop.call_soon_threadsafe(_enqueue_latest, queue, event)
        return event

    def get(self, user_id: str, execution_id: str) -> ExecutionStatusEvent | None:
        with self._lock:
            return self._events.get((user_id.strip(), execution_id.strip()))

    def subscribe(self, user_id: str) -> asyncio.Queue[ExecutionStatusEvent]:
        queue: asyncio.Queue[ExecutionStatusEvent] = asyncio.Queue(self.subscriber_queue_size)
        loop = asyncio.get_running_loop()
        with self._lock:
            self._subscribers.setdefault(user_id.strip(), set()).add((loop, queue))
        return queue

    def unsubscribe(self, user_id: str, queue: asyncio.Queue[ExecutionStatusEvent]) -> None:
        with self._lock:
            subscribers = self._subscribers.get(user_id.strip())
            if subscribers is not None:
                subscribers.difference_update([
                    item for item in subscribers if item[1] is queue
                ])
                if not subscribers:
                    self._subscribers.pop(user_id.strip(), None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
            self._order.clear()
            self._subscribers.clear()


class ExecutionLogStreamRegistry:
    """Fan out persisted execution logs to bounded per-user subscriber queues."""

    def __init__(self, *, subscriber_queue_size: int = 50) -> None:
        self.subscriber_queue_size = subscriber_queue_size
        self._subscribers: dict[
            str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[dict[str, object]]]]
        ] = {}
        self._lock = threading.RLock()

    def publish(self, user_id: str, event: dict[str, object]) -> None:
        with self._lock:
            subscribers = tuple(self._subscribers.get(user_id.strip(), ()))
        for loop, queue in subscribers:
            loop.call_soon_threadsafe(_enqueue_latest, queue, dict(event))

    def subscribe(self, user_id: str) -> asyncio.Queue[dict[str, object]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(self.subscriber_queue_size)
        loop = asyncio.get_running_loop()
        with self._lock:
            self._subscribers.setdefault(user_id.strip(), set()).add((loop, queue))
        return queue

    def unsubscribe(self, user_id: str, queue: asyncio.Queue[dict[str, object]]) -> None:
        with self._lock:
            subscribers = self._subscribers.get(user_id.strip())
            if subscribers is not None:
                subscribers.difference_update([
                    item for item in subscribers if item[1] is queue
                ])
                if not subscribers:
                    self._subscribers.pop(user_id.strip(), None)

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()


execution_status_registry = ExecutionStatusRegistry()
execution_log_stream_registry = ExecutionLogStreamRegistry()


def _enqueue_latest(
    queue: asyncio.Queue[Any], event: Any,
) -> None:
    if queue.full():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    queue.put_nowait(event)


def _response(event: ExecutionStatusEvent) -> ExecutionStatusResponse:
    return ExecutionStatusResponse(
        executionId=event.execution_id,
        status=event.status,
        message=event.message,
        brokerOrderId=event.broker_order_id,
        updatedAt=event.updated_at,
    )


def _websocket_authorized(websocket: WebSocket, ticket: str | None) -> bool:
    if _configured_api_key():
        return _consume_sse_ticket(ticket)
    return _is_local_client(websocket)  # type: ignore[arg-type]


def register_auto_trade_routes(app: Any) -> None:
    @app.get(
        "/auto-trade/execution-logs",
        response_model=list[AutoTradeExecutionLogResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def list_auto_trade_execution_logs(
        user_id: str = Query(..., alias="userId", min_length=1, max_length=128),
        execution_status: ExecutionStatus | None = Query(None, alias="status"),
        level: Literal["INFO", "SIGNAL", "RISK", "ERROR"] | None = Query(None),
        symbol: str | None = Query(None, min_length=1, max_length=32),
        direction: Literal["BUY", "SELL"] | None = Query(None),
        start: datetime | None = Query(None),
        end: datetime | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
    ) -> list[AutoTradeExecutionLogResponse]:
        if start is not None and (start.tzinfo is None or start.utcoffset() is None):
            raise HTTPException(status_code=422, detail="start must include a timezone")
        if end is not None and (end.tzinfo is None or end.utcoffset() is None):
            raise HTTPException(status_code=422, detail="end must include a timezone")
        if start is not None and end is not None and start > end:
            raise HTTPException(status_code=422, detail="start must not be after end")
        with DiagnosticsStore() as store:
            logs = store.auto_trade_execution_logs(
                user_id,
                status=execution_status,
                level=level,
                symbol=symbol.strip().upper() if symbol else None,
                direction=direction,
                start=start.astimezone(timezone.utc).isoformat() if start else None,
                end=end.astimezone(timezone.utc).isoformat() if end else None,
                limit=limit,
            )
        return [AutoTradeExecutionLogResponse.model_validate(item) for item in logs]

    @app.post(
        "/auto-trade/broker-credentials",
        response_model=BrokerCredentialResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def create_broker_credential(
        payload: CreateBrokerCredentialRequest,
    ) -> BrokerCredentialResponse:
        ciphertext, nonce, last_four = _encrypted_values(
            payload, payload.userId, payload.provider,
        )
        try:
            with DiagnosticsStore() as store:
                credential = store.create_encrypted_api_credential(
                    payload.userId, payload.provider, ciphertext, nonce, last_four,
                )
        except EncryptedApiCredentialExistsError as exc:
            raise HTTPException(
                status_code=409, detail="Broker credential already exists"
            ) from exc
        if credential is None:
            raise HTTPException(status_code=404, detail="User not found")
        return BrokerCredentialResponse.model_validate(credential)

    @app.put(
        "/auto-trade/broker-credentials/{provider}",
        response_model=BrokerCredentialResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def update_broker_credential(
        payload: BrokerCredentialValues,
        provider: str = Path(
            ..., min_length=1, max_length=64,
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
        ),
        user_id: str = Query(..., alias="userId", min_length=1, max_length=128),
    ) -> BrokerCredentialResponse:
        ciphertext, nonce, last_four = _encrypted_values(payload, user_id, provider)
        with DiagnosticsStore() as store:
            credential = store.update_encrypted_api_credential(
                user_id, provider, ciphertext, nonce, last_four,
            )
        if credential is None:
            raise HTTPException(status_code=404, detail="Broker credential not found")
        return BrokerCredentialResponse.model_validate(credential)

    @app.post(
        "/auto-trade/broker-credentials/{provider}/rotate",
        response_model=BrokerCredentialResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def rotate_broker_credential(
        payload: BrokerCredentialValues,
        provider: str = Path(
            ..., min_length=1, max_length=64,
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$",
        ),
        user_id: str = Query(..., alias="userId", min_length=1, max_length=128),
    ) -> BrokerCredentialResponse:
        ciphertext, nonce, last_four = _encrypted_values(payload, user_id, provider)
        with DiagnosticsStore() as store:
            credential = store.rotate_encrypted_api_credential(
                user_id, provider, ciphertext, nonce, last_four,
            )
        if credential is None:
            raise HTTPException(status_code=404, detail="Broker credential not found")
        return BrokerCredentialResponse.model_validate(credential)

    @app.post(
        "/auto-trade/configurations",
        response_model=AutoTradeConfigurationResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def create_auto_trade_configuration(
        payload: CreateAutoTradeConfigurationRequest,
    ) -> AutoTradeConfigurationResponse:
        values = payload.model_dump(exclude={"userId"})
        with DiagnosticsStore() as store:
            configuration = store.create_auto_trade_configuration(payload.userId, values)
        if configuration is None:
            raise HTTPException(status_code=404, detail="User not found")
        return AutoTradeConfigurationResponse.model_validate(configuration)

    @app.get(
        "/auto-trade/configurations",
        response_model=list[AutoTradeConfigurationResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def list_auto_trade_configurations(
        user_id: str = Query(..., alias="userId", min_length=1, max_length=128),
    ) -> list[AutoTradeConfigurationResponse]:
        with DiagnosticsStore() as store:
            configurations = store.list_auto_trade_configurations(user_id)
        return [AutoTradeConfigurationResponse.model_validate(item) for item in configurations]

    @app.get(
        "/auto-trade/configurations/{configuration_id}",
        response_model=AutoTradeConfigurationResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def get_auto_trade_configuration(
        configuration_id: str,
        user_id: str = Query(..., alias="userId", min_length=1, max_length=128),
    ) -> AutoTradeConfigurationResponse:
        with DiagnosticsStore() as store:
            configuration = store.get_auto_trade_configuration(user_id, configuration_id)
        if configuration is None:
            raise HTTPException(status_code=404, detail="Auto-trade configuration not found")
        return AutoTradeConfigurationResponse.model_validate(configuration)

    @app.put(
        "/auto-trade/configurations/{configuration_id}",
        response_model=AutoTradeConfigurationResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def update_auto_trade_configuration(
        configuration_id: str,
        payload: AutoTradeConfigurationValues,
        user_id: str = Query(..., alias="userId", min_length=1, max_length=128),
    ) -> AutoTradeConfigurationResponse:
        with DiagnosticsStore() as store:
            configuration = store.update_auto_trade_configuration(
                user_id, configuration_id, payload.model_dump(),
            )
        if configuration is None:
            raise HTTPException(status_code=404, detail="Auto-trade configuration not found")
        return AutoTradeConfigurationResponse.model_validate(configuration)

    @app.delete(
        "/auto-trade/configurations/{configuration_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def delete_auto_trade_configuration(
        configuration_id: str,
        user_id: str = Query(..., alias="userId", min_length=1, max_length=128),
    ) -> Response:
        with DiagnosticsStore() as store:
            deleted = store.delete_auto_trade_configuration(user_id, configuration_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Auto-trade configuration not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get(
        "/auto-trade/executions/{execution_id}/status",
        response_model=ExecutionStatusResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def execution_status(
        execution_id: str,
        user_id: str = Query(..., min_length=1, max_length=128),
    ) -> ExecutionStatusResponse:
        event = execution_status_registry.get(user_id, execution_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Execution status not found")
        return _response(event)

    @app.websocket("/ws/auto-trade/executions")
    async def execution_status_stream(
        websocket: WebSocket,
        user_id: str = Query(..., min_length=1, max_length=128),
        ticket: str | None = Query(None),
    ) -> None:
        if not _websocket_authorized(websocket, ticket):
            await websocket.close(code=4401, reason="Unauthorized")
            return
        await websocket.accept()
        queue = execution_status_registry.subscribe(user_id)
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(_response(event).model_dump())
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        finally:
            execution_status_registry.unsubscribe(user_id, queue)

    @app.websocket("/ws/auto-trade/execution-logs")
    async def execution_log_stream(
        websocket: WebSocket,
        user_id: str = Query(..., alias="userId", min_length=1, max_length=128),
        ticket: str | None = Query(None),
    ) -> None:
        if not _websocket_authorized(websocket, ticket):
            await websocket.close(code=4401, reason="Unauthorized")
            return
        await websocket.accept()
        queue = execution_log_stream_registry.subscribe(user_id)
        try:
            while True:
                event = await queue.get()
                response = AutoTradeExecutionLogResponse.model_validate(event)
                await websocket.send_json(response.model_dump())
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        finally:
            execution_log_stream_registry.unsubscribe(user_id, queue)
