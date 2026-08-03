from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from src.trading.auto_trade import BrokerOrderRequest, TradeExecutionQueue


NOW = datetime(2026, 8, 1, 9, tzinfo=timezone.utc)


def _request(key):
    return BrokerOrderRequest(key, "mt5-paper", "XAUUSD", "buy", 0.05)


def test_queue_returns_only_due_trades_in_schedule_order():
    queue = TradeExecutionQueue()
    assert queue.schedule(_request("later"), NOW + timedelta(minutes=2)) is True
    assert queue.schedule(_request("first"), NOW) is True

    assert [item.request.idempotency_key for item in queue.pending()] == ["first", "later"]
    assert queue.pop_due(NOW - timedelta(seconds=1)) is None
    assert queue.pop_due(NOW).request.idempotency_key == "first"
    assert queue.pop_due(NOW + timedelta(minutes=1)) is None
    assert queue.pop_due(NOW + timedelta(minutes=2)).request.idempotency_key == "later"


def test_duplicate_key_is_suppressed_before_and_after_dequeue():
    queue = TradeExecutionQueue()
    request = _request("same-signal")

    assert queue.schedule(request, NOW) is True
    assert queue.schedule(request, NOW + timedelta(seconds=1)) is False
    assert queue.pop_due(NOW) is not None
    assert queue.schedule(request, NOW + timedelta(seconds=2)) is False


def test_concurrent_producers_enqueue_duplicate_once():
    queue = TradeExecutionQueue()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: queue.schedule(_request("one"), NOW), range(20)))

    assert results.count(True) == 1
    assert len(queue) == 1


def test_queue_validates_capacity_and_aware_times():
    queue = TradeExecutionQueue(maximum_size=1)
    queue.schedule(_request("one"), NOW)
    with pytest.raises(OverflowError):
        queue.schedule(_request("two"), NOW)
    with pytest.raises(ValueError):
        TradeExecutionQueue().schedule(_request("naive"), datetime(2026, 8, 1))
