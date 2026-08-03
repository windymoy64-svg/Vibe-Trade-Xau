from fastapi.testclient import TestClient

import api_server
from src.api.precision_execution_routes import precision_dataset_store


CSV = b"""timestamp,open,high,low,close,volume
2026-08-01T08:00:00Z,2380,2386,2379,2384,100
2026-08-01T08:15:00Z,2384,2391,2383,2389,120
"""


def setup_function():
    precision_dataset_store.clear()


def test_upload_returns_metadata_and_user_scoped_memory_dataset():
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).post(
        "/precision-execution/ohlcv",
        data={"userId": "alice", "symbol": "xauusd", "timeframe": "m15"},
        files={"file": ("xauusd.csv", CSV, "text/csv")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["symbol"] == "XAUUSD"
    assert payload["timeframe"] == "M15"
    assert payload["rowCount"] == 2
    assert precision_dataset_store.get("alice", payload["datasetId"]) is not None
    assert precision_dataset_store.get("bob", payload["datasetId"]) is None


def test_upload_rejects_invalid_extension_and_oversized_content():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    unsupported = client.post(
        "/precision-execution/ohlcv",
        data={"symbol": "XAUUSD", "timeframe": "M15"},
        files={"file": ("data.txt", CSV, "text/plain")},
    )
    oversized = client.post(
        "/precision-execution/ohlcv",
        data={"symbol": "XAUUSD", "timeframe": "M15"},
        files={"file": ("data.csv", b"x" * (5 * 1024 * 1024 + 1), "text/csv")},
    )

    assert unsupported.status_code == 422
    assert oversized.status_code == 422
