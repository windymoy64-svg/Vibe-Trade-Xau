from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import api_server
from src.api.precision_execution_routes import precision_dataset_store


def setup_function():
    precision_dataset_store.clear()


def _csv(row_count: int) -> bytes:
    start = datetime(2026, 8, 1, tzinfo=timezone.utc)
    rows = ["timestamp,open,high,low,close,volume"]
    closes = [100, 102, 105, 103, 100, 107, 104, 101, 98, 102, 106, 103]
    for index in range(row_count):
        close = closes[index % len(closes)]
        timestamp = start + timedelta(minutes=15 * index)
        rows.append(
            f"{timestamp.isoformat()},{close - 0.5},{close + 1},{close - 1},{close},100"
        )
    return ("\n".join(rows) + "\n").encode()


def _upload(client: TestClient, *, user_id: str = "alice", row_count: int = 24) -> str:
    response = client.post(
        "/precision-execution/ohlcv",
        data={"userId": user_id, "symbol": "xauusd", "timeframe": "m15"},
        files={"file": ("xauusd.csv", _csv(row_count), "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["datasetId"]


def test_analyze_uploaded_dataset_returns_contract_sections_and_metadata():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    dataset_id = _upload(client)

    response = client.post(
        "/precision-execution/analyze",
        json={"userId": "alice", "datasetId": dataset_id, "pipSize": 0.1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset"] == {
        "datasetId": dataset_id,
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "rowCount": 24,
        "startAt": "2026-08-01T00:00:00+00:00",
        "endAt": "2026-08-01T05:45:00+00:00",
    }
    assert payload["currentPrice"] == 103
    assert payload["bias"] in {"BULLISH", "BEARISH", "NEUTRAL"}
    assert payload["generatedAt"]
    assert set(payload) == {
        "dataset", "currentPrice", "bias", "generatedAt", "marketStructure",
        "supplyDemandZones", "acrZones", "reversalSignals", "fairValueGaps",
        "confluences", "fibonacci", "orderRecommendation", "tradeLevels",
    }
    assert set(payload["marketStructure"]) == {"bias", "swings", "breaks"}
    assert isinstance(payload["supplyDemandZones"], list)
    assert isinstance(payload["acrZones"], list)
    assert isinstance(payload["reversalSignals"], list)
    assert isinstance(payload["fairValueGaps"], list)
    assert isinstance(payload["confluences"], list)
    if payload["orderRecommendation"]["recommendation"] == "WAIT":
        assert payload["tradeLevels"] is None


def test_analyze_is_user_scoped():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    dataset_id = _upload(client)

    response = client.post(
        "/precision-execution/analyze",
        json={"userId": "bob", "datasetId": dataset_id, "pipSize": 0.1},
    )

    assert response.status_code == 404


def test_analyze_rejects_too_short_dataset():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    dataset_id = _upload(client, row_count=2)

    response = client.post(
        "/precision-execution/analyze",
        json={"userId": "alice", "datasetId": dataset_id, "pipSize": 0.1},
    )

    assert response.status_code == 422
    assert "insufficient" in response.json()["detail"]


def test_analyze_rejects_non_positive_pip_size():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    dataset_id = _upload(client)

    response = client.post(
        "/precision-execution/analyze",
        json={"userId": "alice", "datasetId": dataset_id, "pipSize": 0},
    )

    assert response.status_code == 422
