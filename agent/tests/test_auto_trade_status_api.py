import asyncio

from fastapi.testclient import TestClient

import api_server
from src.api.auto_trade_routes import execution_log_stream_registry, execution_status_registry


def setup_function():
    execution_status_registry.clear()
    execution_log_stream_registry.clear()


def test_execution_status_endpoint_is_user_scoped():
    asyncio.run(execution_status_registry.publish(
        "alice", "exec-1", "PENDING", "Order accepted by queue.", broker_order_id="1842",
    ))
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))

    response = client.get(
        "/auto-trade/executions/exec-1/status", params={"user_id": "alice"},
    )

    assert response.status_code == 200
    assert response.json()["executionId"] == "exec-1"
    assert response.json()["status"] == "PENDING"
    assert response.json()["brokerOrderId"] == "1842"
    assert client.get(
        "/auto-trade/executions/exec-1/status", params={"user_id": "bob"},
    ).status_code == 404


def test_execution_websocket_streams_only_subscribed_user():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    with client.websocket_connect(
        "/ws/auto-trade/executions?user_id=alice",
    ) as websocket:
        asyncio.run(execution_status_registry.publish(
            "bob", "private", "FAILED", "Bob only.",
        ))
        asyncio.run(execution_status_registry.publish(
            "alice", "exec-2", "EXECUTED", "Order filled.", broker_order_id="1843",
        ))
        event = websocket.receive_json()

    assert event["executionId"] == "exec-2"
    assert event["status"] == "EXECUTED"
    assert event["message"] == "Order filled."


def test_execution_log_websocket_streams_frontend_contract():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    with client.websocket_connect(
        "/ws/auto-trade/execution-logs?userId=alice",
    ) as websocket:
        execution_log_stream_registry.publish("bob", {
            "id": "private", "level": "INFO", "status": "PENDING",
            "message": "Bob", "symbol": None, "direction": None,
            "strategyId": None, "lotSize": None, "price": None,
            "stopLoss": None, "takeProfit": None, "brokerOrderId": None,
            "errorCode": None, "timestamp": "2026-08-01T09:00:00Z",
        })
        execution_log_stream_registry.publish("alice", {
            "id": "log-1", "level": "SIGNAL", "status": "EXECUTED",
            "message": "Order filled.", "symbol": "XAUUSD", "direction": "BUY",
            "strategyId": "trend", "lotSize": 0.05, "price": 2389.8,
            "stopLoss": 2383.8, "takeProfit": 2401.8, "brokerOrderId": "1842",
            "errorCode": None, "timestamp": "2026-08-01T09:00:00Z",
        })
        event = websocket.receive_json()

    assert event["id"] == "log-1"
    assert event["level"] == "SIGNAL"
    assert event["price"] == 2389.8
