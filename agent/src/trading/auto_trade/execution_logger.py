"""Durable, credential-free audit logging for auto-trade execution events."""

from __future__ import annotations

import math
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol

LogLevel = Literal["INFO", "SIGNAL", "RISK", "ERROR"]
LogStatus = Literal["MONITORING", "PENDING", "EXECUTED", "REJECTED", "CLOSED", "FAILED"]


class ExecutionLogSink(Protocol):
    def append_auto_trade_execution_log(
        self, user_id: str, values: dict[str, object],
    ) -> dict[str, object] | None: ...


@dataclass(frozen=True, slots=True)
class ExecutionLogEvent:
    user_id: str
    status: LogStatus
    message: str
    timestamp: datetime
    level: LogLevel = "INFO"
    symbol: str | None = None
    direction: Literal["BUY", "SELL"] | None = None
    strategy_id: str | None = None
    lot_size: float | None = None
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    broker_order_id: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.user_id.strip() or not self.message.strip():
            raise ValueError("user and log message are required")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("log timestamp must be timezone-aware")
        numeric = (self.lot_size, self.price, self.stop_loss, self.take_profit)
        if any(value is not None and (not math.isfinite(value) or value <= 0) for value in numeric):
            raise ValueError("log prices and lot size must be positive and finite")


class ExecutionLogUserNotFoundError(ValueError):
    pass


class AutoTradeExecutionLogger:
    def __init__(
        self,
        sink: ExecutionLogSink,
        publisher: Callable[[str, dict[str, object]], None] | None = None,
    ) -> None:
        self._sink = sink
        self._publisher = publisher

    def record(self, event: ExecutionLogEvent) -> dict[str, object]:
        values: dict[str, object] = {
            "id": str(uuid.uuid4()),
            "level": event.level,
            "status": event.status,
            "message": event.message.strip(),
            "symbol": event.symbol.strip().upper() if event.symbol else None,
            "direction": event.direction,
            "strategyId": event.strategy_id,
            "lotSize": event.lot_size,
            "price": event.price,
            "stopLoss": event.stop_loss,
            "takeProfit": event.take_profit,
            "brokerOrderId": event.broker_order_id,
            "errorCode": event.error_code,
            "timestamp": event.timestamp.astimezone(timezone.utc).isoformat(),
        }
        persisted = self._sink.append_auto_trade_execution_log(event.user_id.strip(), values)
        if persisted is None:
            raise ExecutionLogUserNotFoundError("execution log user not found")
        if self._publisher is not None:
            self._publisher(event.user_id.strip(), persisted)
        return persisted
