"""Thread-safe scheduled trade queue with strict duplicate suppression."""

from __future__ import annotations

import heapq
import itertools
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .broker_order_service import BrokerOrderRequest


@dataclass(frozen=True, slots=True)
class ScheduledTrade:
    execute_at: datetime
    request: BrokerOrderRequest
    _sequence: int = field(default=0, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.execute_at.tzinfo is None or self.execute_at.utcoffset() is None:
            raise ValueError("execution time must be timezone-aware")


class TradeExecutionQueue:
    """Schedule each broker idempotency key at most once per process."""

    def __init__(self, *, maximum_size: int = 1000) -> None:
        if maximum_size <= 0:
            raise ValueError("maximum size must be positive")
        self.maximum_size = maximum_size
        self._heap: list[tuple[datetime, int, ScheduledTrade]] = []
        self._seen_keys: set[str] = set()
        self._sequence = itertools.count()
        self._lock = threading.RLock()

    def schedule(self, request: BrokerOrderRequest, execute_at: datetime) -> bool:
        if execute_at.tzinfo is None or execute_at.utcoffset() is None:
            raise ValueError("execution time must be timezone-aware")
        item = ScheduledTrade(execute_at.astimezone(timezone.utc), request)
        key = request.idempotency_key.strip()
        with self._lock:
            if key in self._seen_keys:
                return False
            if len(self._heap) >= self.maximum_size:
                raise OverflowError("trade execution queue is full")
            sequence = next(self._sequence)
            item = ScheduledTrade(item.execute_at, request, sequence)
            heapq.heappush(self._heap, (item.execute_at, sequence, item))
            self._seen_keys.add(key)
        return True

    def pop_due(self, now: datetime) -> ScheduledTrade | None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("current time must be timezone-aware")
        normalized_now = now.astimezone(timezone.utc)
        with self._lock:
            if not self._heap or self._heap[0][0] > normalized_now:
                return None
            return heapq.heappop(self._heap)[2]

    def pending(self) -> tuple[ScheduledTrade, ...]:
        with self._lock:
            return tuple(item[2] for item in sorted(self._heap))

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)
