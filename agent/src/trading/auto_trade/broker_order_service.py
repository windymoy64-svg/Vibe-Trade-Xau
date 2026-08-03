"""Safe application boundary for submitting auto-trade orders to broker APIs."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

OrderSide = Literal["buy", "sell"]
OrderStatus = Literal["ACCEPTED", "REJECTED", "ERROR"]


@dataclass(frozen=True, slots=True)
class BrokerOrderRequest:
    idempotency_key: str
    profile_id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: str = "market"
    limit_price: float | None = None
    time_in_force: str = "day"
    session_id: str = ""

    def __post_init__(self) -> None:
        if not self.idempotency_key.strip() or not self.profile_id.strip() or not self.symbol.strip():
            raise ValueError("idempotency key, profile, and symbol are required")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type == "limit" and self.limit_price is None:
            raise ValueError("limit price is required for limit orders")
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("limit price must be positive")


@dataclass(frozen=True, slots=True)
class BrokerOrderResult:
    status: OrderStatus
    broker_order_id: str | None
    message: str
    broker_response: dict[str, Any]


class DuplicateBrokerOrderError(ValueError):
    pass


class BrokerOrderService:
    """Submit each idempotency key once through the protected trading service."""

    def __init__(self, submitter: Callable[..., dict[str, Any]] | None = None) -> None:
        self._submitter = submitter
        self._submitted_keys: set[str] = set()
        self._lock = threading.RLock()

    def submit(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        key = request.idempotency_key.strip()
        with self._lock:
            if key in self._submitted_keys:
                raise DuplicateBrokerOrderError("duplicate broker order idempotency key")
            self._submitted_keys.add(key)

        submitter = self._submitter
        if submitter is None:
            from src.trading.service import place_order

            submitter = place_order
        try:
            response = submitter(
                request.symbol.strip().upper(),
                request.profile_id.strip(),
                side=request.side,
                quantity=request.quantity,
                order_type=request.order_type,
                limit_price=request.limit_price,
                time_in_force=request.time_in_force,
                session_id=request.session_id,
            )
        except Exception as exc:  # Broker/network errors become auditable results.
            return BrokerOrderResult("ERROR", None, str(exc) or exc.__class__.__name__, {})

        payload = response if isinstance(response, dict) else {"raw": response}
        accepted = str(payload.get("status", "")).strip().lower() in {
            "ok", "accepted", "filled", "pending",
        }
        order_id = payload.get("order_id") or payload.get("orderId") or payload.get("order")
        error = payload.get("error") or payload.get("message") or payload.get("detail")
        return BrokerOrderResult(
            "ACCEPTED" if accepted else "REJECTED",
            str(order_id) if order_id is not None else None,
            str(error or ("Broker accepted order." if accepted else "Broker rejected order.")),
            payload,
        )
