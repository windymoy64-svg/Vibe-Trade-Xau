from fastapi.testclient import TestClient

import api_server
from src.diagnostics.store import DiagnosticsStore


def _payload(user_id: str = "alice") -> dict[str, object]:
    return {
        "userId": user_id,
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "strategy": "Evidence trend guard",
        "riskPerTrade": 0.5,
        "dailyLossLimit": 2,
        "paperMode": True,
        "robotControls": {
            "enabled": False,
            "lotSize": 0.05,
            "stopLossPips": 30,
            "takeProfitPips": 60,
        },
    }


def _prepare_users(db_path) -> None:
    with DiagnosticsStore(db_path) as store:
        with store._conn:
            for user_id in ("alice", "bob"):
                store._conn.execute(
                    """INSERT INTO users (
                        id, email, name, password_hash, created_at, updated_at, last_active_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, f"{user_id}@example.com", user_id.title(), "x" * 32,
                     "now", "now", "now"),
                )


def test_auto_trade_configuration_crud_contract_is_user_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "config-api.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    _prepare_users(db_path)
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))

    created_response = client.post("/auto-trade/configurations", json=_payload())
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["userId"] == "alice"
    assert created["robotControls"]["lotSize"] == 0.05

    config_id = created["id"]
    assert client.get(
        "/auto-trade/configurations", params={"userId": "alice"},
    ).json() == [created]
    assert client.get(
        f"/auto-trade/configurations/{config_id}", params={"userId": "bob"},
    ).status_code == 404

    replacement = _payload()
    replacement.pop("userId")
    replacement["paperMode"] = False
    replacement["riskPerTrade"] = 1.25
    updated_response = client.put(
        f"/auto-trade/configurations/{config_id}",
        params={"userId": "alice"},
        json=replacement,
    )
    assert updated_response.status_code == 200
    assert updated_response.json()["paperMode"] is False
    assert updated_response.json()["riskPerTrade"] == 1.25

    assert client.delete(
        f"/auto-trade/configurations/{config_id}", params={"userId": "bob"},
    ).status_code == 404
    deleted_response = client.delete(
        f"/auto-trade/configurations/{config_id}", params={"userId": "alice"},
    )
    assert deleted_response.status_code == 204
    assert deleted_response.content == b""
    assert client.get(
        f"/auto-trade/configurations/{config_id}", params={"userId": "alice"},
    ).status_code == 404


def test_auto_trade_configuration_rejects_unsafe_limits(tmp_path, monkeypatch):
    db_path = tmp_path / "config-limits.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    _prepare_users(db_path)
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))

    payload = _payload()
    payload["riskPerTrade"] = 5.01
    assert client.post("/auto-trade/configurations", json=payload).status_code == 422

    payload = _payload()
    payload["robotControls"]["stopLossPips"] = 4.99
    assert client.post("/auto-trade/configurations", json=payload).status_code == 422


def test_auto_trade_configuration_requires_existing_user(tmp_path, monkeypatch):
    db_path = tmp_path / "config-user.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    with DiagnosticsStore(db_path):
        pass
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))

    assert client.post("/auto-trade/configurations", json=_payload()).status_code == 404
