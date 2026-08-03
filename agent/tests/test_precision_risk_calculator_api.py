from fastapi.testclient import TestClient

import api_server


def test_risk_calculator_uses_xauusd_defaults_and_camel_case_contract():
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).post(
        "/precision-execution/risk-calculator",
        json={
            "balance": 10_000, "riskPercentage": 1,
            "entryPrice": 2400, "stopLoss": 2395,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "balance": 10000.0,
        "riskPercentage": 1.0,
        "riskAmount": 100.0,
        "stopDistance": 5.0,
        "lotSize": 0.2,
        "actualRiskAmount": 100.0,
        "boundedBy": None,
    }


def test_risk_calculator_validates_limits_and_zero_stop_distance():
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    assert client.post(
        "/precision-execution/risk-calculator",
        json={"balance": 99, "riskPercentage": 1, "entryPrice": 100, "stopLoss": 90},
    ).status_code == 422
    assert client.post(
        "/precision-execution/risk-calculator",
        json={"balance": 1000, "riskPercentage": 6, "entryPrice": 100, "stopLoss": 90},
    ).status_code == 422
    zero_stop = client.post(
        "/precision-execution/risk-calculator",
        json={"balance": 1000, "riskPercentage": 1, "entryPrice": 100, "stopLoss": 100},
    )
    assert zero_stop.status_code == 422
    assert "zero stop" in zero_stop.json()["detail"]
