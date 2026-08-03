import base64
import os

from fastapi.testclient import TestClient

import api_server
from src.diagnostics.store import DiagnosticsStore
from src.trading.auto_trade import BrokerCredentialEncryptionService


def _prepare_users(db_path) -> None:
    with DiagnosticsStore(db_path) as store:
        with store._conn:
            for user_id in ("alice", "bob"):
                store._conn.execute(
                    """INSERT INTO users (
                        id, email, name, password_hash, created_at, updated_at, last_active_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id, f"{user_id}@example.com", user_id.title(),
                        "x" * 32, "now", "now", "now",
                    ),
                )


def _configure(tmp_path, monkeypatch):
    db_path = tmp_path / "broker-credentials.db"
    encoded_key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    monkeypatch.setenv("VIBE_TRADING_CREDENTIAL_ENCRYPTION_KEY", encoded_key)
    _prepare_users(db_path)
    return db_path, encoded_key


def _stored_credential(db_path, user_id="alice", provider="MT5"):
    with DiagnosticsStore(db_path) as store:
        return store._conn.execute(
            """SELECT ciphertext, nonce, key_version, last_four, created_at, updated_at
                FROM encrypted_api_credentials WHERE user_id = ? AND provider = ?""",
            (user_id, provider),
        ).fetchone()


def test_broker_credential_create_update_rotate_contract(tmp_path, monkeypatch):
    db_path, _ = _configure(tmp_path, monkeypatch)
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    service = BrokerCredentialEncryptionService.from_environment()

    created_response = client.post(
        "/auto-trade/broker-credentials",
        json={"userId": "alice", "provider": "MT5", "apiKey": "first-secret-A1B2"},
    )
    assert created_response.status_code == 201
    created = created_response.json()
    assert set(created) == {"provider", "lastFour", "keyVersion", "createdAt", "updatedAt"}
    assert created == {
        "provider": "MT5", "lastFour": "A1B2", "keyVersion": 1,
        "createdAt": created["createdAt"], "updatedAt": created["updatedAt"],
    }

    first = _stored_credential(db_path)
    assert b"first-secret-A1B2" not in bytes(first["ciphertext"])
    assert b"first-secret-A1B2" not in db_path.read_bytes()
    assert len(first["nonce"]) == 12
    assert service.decrypt(
        first["ciphertext"], first["nonce"], user_id="alice", provider="MT5",
    ) == "first-secret-A1B2"
    first_nonce = bytes(first["nonce"])

    duplicate = client.post(
        "/auto-trade/broker-credentials",
        json={"userId": "alice", "provider": "MT5", "apiKey": "duplicate-key-C3D4"},
    )
    assert duplicate.status_code == 409

    updated_response = client.put(
        "/auto-trade/broker-credentials/MT5",
        params={"userId": "alice"},
        json={"apiKey": "updated-secret-E5F6"},
    )
    assert updated_response.status_code == 200
    assert updated_response.json()["keyVersion"] == 1
    updated = _stored_credential(db_path)
    assert bytes(updated["nonce"]) != first_nonce
    assert service.decrypt(
        updated["ciphertext"], updated["nonce"], user_id="alice", provider="MT5",
    ) == "updated-secret-E5F6"

    rotated_response = client.post(
        "/auto-trade/broker-credentials/MT5/rotate",
        params={"userId": "alice"},
        json={"apiKey": "rotated-secret-G7H8"},
    )
    assert rotated_response.status_code == 200
    assert rotated_response.json()["keyVersion"] == 2
    rotated = _stored_credential(db_path)
    assert bytes(rotated["nonce"]) != bytes(updated["nonce"])
    assert service.decrypt(
        rotated["ciphertext"], rotated["nonce"], user_id="alice", provider="MT5",
    ) == "rotated-secret-G7H8"


def test_broker_credentials_are_user_scoped_and_validate_input(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    payload = {"userId": "alice", "provider": "MT5", "apiKey": "secret-key-A1B2"}
    assert client.post("/auto-trade/broker-credentials", json=payload).status_code == 201

    assert client.put(
        "/auto-trade/broker-credentials/MT5",
        params={"userId": "bob"},
        json={"apiKey": "other-secret-C3D4"},
    ).status_code == 404
    assert client.post(
        "/auto-trade/broker-credentials/MT5/rotate",
        params={"userId": "bob"},
        json={"apiKey": "other-secret-C3D4"},
    ).status_code == 404
    assert client.post(
        "/auto-trade/broker-credentials",
        json={**payload, "provider": "../MT5"},
    ).status_code == 422
    assert client.post(
        "/auto-trade/broker-credentials",
        json={**payload, "apiKey": " secret-A1B2"},
    ).status_code == 422


def test_broker_credentials_fail_closed_without_valid_master_key(tmp_path, monkeypatch):
    db_path = tmp_path / "missing-key.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    monkeypatch.delenv("VIBE_TRADING_CREDENTIAL_ENCRYPTION_KEY", raising=False)
    _prepare_users(db_path)
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    payload = {"userId": "alice", "provider": "MT5", "apiKey": "secret-key-A1B2"}

    assert client.post("/auto-trade/broker-credentials", json=payload).status_code == 503
    monkeypatch.setenv("VIBE_TRADING_CREDENTIAL_ENCRYPTION_KEY", "not-base64!")
    assert client.post("/auto-trade/broker-credentials", json=payload).status_code == 503
    monkeypatch.setenv(
        "VIBE_TRADING_CREDENTIAL_ENCRYPTION_KEY",
        base64.urlsafe_b64encode(os.urandom(16)).decode("ascii"),
    )
    assert client.post("/auto-trade/broker-credentials", json=payload).status_code == 503


def test_broker_credential_routes_require_auth_for_non_local_clients(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    monkeypatch.setenv("API_AUTH_KEY", "route-auth-secret")
    client = TestClient(api_server.app, client=("203.0.113.10", 50000))
    payload = {"userId": "alice", "provider": "MT5", "apiKey": "secret-key-A1B2"}

    assert client.post("/auto-trade/broker-credentials", json=payload).status_code == 401
    response = client.post(
        "/auto-trade/broker-credentials",
        headers={"Authorization": "Bearer route-auth-secret"},
        json=payload,
    )
    assert response.status_code == 201
