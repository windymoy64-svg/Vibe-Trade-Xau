"""Contract tests for local account registration and login."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.auth_routes import InMemoryAccountStore, register_auth_routes


def _client() -> tuple[TestClient, InMemoryAccountStore]:
    app = FastAPI()
    store = InMemoryAccountStore()
    register_auth_routes(app, require_auth=lambda: None, account_store=store)
    return TestClient(app), store


def test_register_creates_safe_normalized_account() -> None:
    client, store = _client()

    response = client.post(
        "/auth/register",
        json={"name": "  Alex   Morgan  ", "email": " Trader@Example.COM ", "password": "secure-pass-123"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "name": "Alex Morgan",
        "email": "trader@example.com",
        "createdAt": response.json()["createdAt"],
    }
    stored = store._users_by_email["trader@example.com"]
    assert stored["password_hash"].startswith("scrypt$16384$8$1$")
    assert "secure-pass-123" not in stored["password_hash"]
    assert "password" not in response.text.lower()


def test_register_rejects_case_insensitive_duplicate_email() -> None:
    client, _ = _client()
    payload = {"name": "Alex Morgan", "email": "trader@example.com", "password": "secure-pass-123"}

    assert client.post("/auth/register", json=payload).status_code == 201
    response = client.post("/auth/register", json={**payload, "email": "TRADER@example.com"})

    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists"


def test_register_validates_name_email_and_password() -> None:
    client, _ = _client()

    cases = [
        {"name": " ", "email": "trader@example.com", "password": "secure-pass-123"},
        {"name": "Alex Morgan", "email": "not-an-email", "password": "secure-pass-123"},
        {"name": "Alex Morgan", "email": "trader@example.com", "password": "short"},
    ]
    for payload in cases:
        assert client.post("/auth/register", json=payload).status_code == 422


def test_login_authenticates_registered_account_with_normalized_email() -> None:
    client, _ = _client()
    registration = {"name": "Alex Morgan", "email": "trader@example.com", "password": "secure-pass-123"}
    registered = client.post("/auth/register", json=registration).json()

    response = client.post(
        "/auth/login",
        json={"email": " TRADER@Example.COM ", "password": "secure-pass-123"},
    )

    assert response.status_code == 200
    assert response.json() == registered
    assert "password" not in response.text.lower()


def test_login_uses_generic_unauthorized_response_for_invalid_credentials() -> None:
    client, _ = _client()
    client.post(
        "/auth/register",
        json={"name": "Alex Morgan", "email": "trader@example.com", "password": "secure-pass-123"},
    )

    cases = [
        {"email": "trader@example.com", "password": "wrong-password"},
        {"email": "missing@example.com", "password": "secure-pass-123"},
    ]
    for payload in cases:
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password"}
        assert response.headers["www-authenticate"] == "Bearer"


def test_login_rejects_invalid_payload_and_corrupt_hash() -> None:
    client, store = _client()
    assert client.post("/auth/login", json={"email": "invalid", "password": "secret"}).status_code == 422

    store._users_by_email["trader@example.com"] = {
        "id": "user-1",
        "name": "Alex Morgan",
        "email": "trader@example.com",
        "password_hash": "not-a-valid-hash",
        "createdAt": "2026-07-31T00:00:00Z",
    }
    response = client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "secure-pass-123"},
    )
    assert response.status_code == 401


def test_profile_get_and_put_update_user_scoped_fields() -> None:
    client, _ = _client()
    registered = client.post(
        "/auth/register",
        json={"name": "Alex Morgan", "email": "trader@example.com", "password": "secure-pass-123"},
    ).json()

    response = client.get("/user/profile", params={"user_id": registered["id"]})
    assert response.status_code == 200
    assert response.json() == {
        "id": registered["id"],
        "name": "Alex Morgan",
        "email": "trader@example.com",
        "role": "Strategy owner",
        "timezone": "UTC",
        "tradingFocus": "XAUUSD intraday",
        "bio": "",
        "joinedAt": registered["createdAt"],
        "lastActiveAt": registered["createdAt"],
    }

    updated = client.put(
        "/user/profile",
        params={"user_id": registered["id"]},
        json={
            "name": "  Alex   Trader ",
            "email": " ALEX@EXAMPLE.COM ",
            "role": " Strategy analyst ",
            "timezone": "Asia/Jakarta",
            "tradingFocus": "XAUUSD swing",
            "bio": " Evidence-led strategy review. ",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Alex Trader"
    assert updated.json()["email"] == "alex@example.com"
    assert updated.json()["role"] == "Strategy analyst"
    assert updated.json()["bio"] == "Evidence-led strategy review."
    assert updated.json()["lastActiveAt"] >= updated.json()["joinedAt"]
    assert client.post(
        "/auth/login",
        json={"email": "alex@example.com", "password": "secure-pass-123"},
    ).status_code == 200


def test_profile_returns_not_found_and_rejects_duplicate_email() -> None:
    client, _ = _client()
    first = client.post(
        "/auth/register",
        json={"name": "First User", "email": "first@example.com", "password": "secure-pass-123"},
    ).json()
    client.post(
        "/auth/register",
        json={"name": "Second User", "email": "second@example.com", "password": "secure-pass-456"},
    )

    assert client.get("/user/profile", params={"user_id": "missing"}).status_code == 404
    response = client.put(
        "/user/profile",
        params={"user_id": first["id"]},
        json={"name": "First User", "email": "second@example.com"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists"


def test_profile_update_validates_payload_and_requires_user_id() -> None:
    client, _ = _client()
    assert client.get("/user/profile").status_code == 422
    response = client.put(
        "/user/profile",
        params={"user_id": "user-1"},
        json={"name": " ", "email": "invalid", "bio": "x" * 241},
    )
    assert response.status_code == 422


def test_change_password_replaces_hash_and_login_credential() -> None:
    client, store = _client()
    registered = client.post(
        "/auth/register",
        json={"name": "Alex Morgan", "email": "trader@example.com", "password": "secure-pass-123"},
    ).json()
    old_hash = store._users_by_id[registered["id"]]["password_hash"]

    response = client.put(
        "/user/password",
        params={"user_id": registered["id"]},
        json={
            "currentPassword": "secure-pass-123",
            "newPassword": "new-secure-pass-456",
            "confirmPassword": "new-secure-pass-456",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "password_updated"}
    new_hash = store._users_by_id[registered["id"]]["password_hash"]
    assert new_hash != old_hash
    assert "new-secure-pass-456" not in new_hash
    assert client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "secure-pass-123"},
    ).status_code == 401
    assert client.post(
        "/auth/login",
        json={"email": "trader@example.com", "password": "new-secure-pass-456"},
    ).status_code == 200


def test_change_password_rejects_wrong_current_password_without_mutation() -> None:
    client, store = _client()
    registered = client.post(
        "/auth/register",
        json={"name": "Alex Morgan", "email": "trader@example.com", "password": "secure-pass-123"},
    ).json()
    old_hash = store._users_by_id[registered["id"]]["password_hash"]

    response = client.put(
        "/user/password",
        params={"user_id": registered["id"]},
        json={
            "currentPassword": "wrong-password",
            "newPassword": "new-secure-pass-456",
            "confirmPassword": "new-secure-pass-456",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Current password is invalid"}
    assert response.headers["www-authenticate"] == "Bearer"
    assert store._users_by_id[registered["id"]]["password_hash"] == old_hash


def test_change_password_validates_confirmation_and_user() -> None:
    client, _ = _client()
    base = {
        "currentPassword": "secure-pass-123",
        "newPassword": "new-secure-pass-456",
        "confirmPassword": "different-pass-789",
    }
    assert client.put("/user/password", params={"user_id": "missing"}, json=base).status_code == 422
    same_password = {
        "currentPassword": "secure-pass-123",
        "newPassword": "secure-pass-123",
        "confirmPassword": "secure-pass-123",
    }
    assert client.put("/user/password", params={"user_id": "missing"}, json=same_password).status_code == 422
    valid = {**base, "confirmPassword": "new-secure-pass-456"}
    assert client.put("/user/password", params={"user_id": "missing"}, json=valid).status_code == 404
    assert client.put("/user/password", json=valid).status_code == 422
