"""Account registration and short-lived SSE auth-ticket routes.

Mounted by ``agent/api_server.py`` via ``register_auth_routes(app, ...)``.

A browser ``EventSource`` cannot send an ``Authorization`` header, so instead of
putting the long-lived API key in the SSE URL (where it leaks into browser
history, proxy/access logs, and Referer headers) the frontend exchanges the
header-authenticated key for a one-shot ticket here, then opens the stream with
``?ticket=``. The ticket store + validation live in ``src.api.security``.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Literal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator

from src.diagnostics.store import DiagnosticsStore

AuthDep = Callable[..., Awaitable[Any] | Any]
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class RegisterRequest(BaseModel):
    """Public account-registration payload."""

    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=1024)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("name must contain at least 2 characters")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("invalid email address")
        return normalized


class RegisteredUserResponse(BaseModel):
    """Safe account representation; credentials are never serialized."""

    id: str
    name: str
    email: str
    createdAt: str


class LoginRequest(BaseModel):
    """Email/password credentials accepted by the local login endpoint."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("invalid email address")
        return normalized


class UserProfileResponse(BaseModel):
    """Editable diagnostics identity and trading-context profile."""

    id: str
    name: str
    email: str
    role: str
    timezone: str
    tradingFocus: str
    bio: str
    joinedAt: str
    lastActiveAt: str


class UpdateUserProfileRequest(BaseModel):
    """User-editable profile fields."""

    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    role: str = Field(default="", max_length=120)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    tradingFocus: str = Field(default="", max_length=120)
    bio: str = Field(default="", max_length=240)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("name must contain at least 2 characters")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError("invalid email address")
        return normalized

    @field_validator("role", "timezone", "tradingFocus", "bio")
    @classmethod
    def strip_profile_text(cls, value: str) -> str:
        return value.strip()


class ChangePasswordRequest(BaseModel):
    """Current credentials plus the confirmed replacement password."""

    currentPassword: str = Field(min_length=1, max_length=1024)
    newPassword: str = Field(min_length=8, max_length=1024)
    confirmPassword: str = Field(min_length=8, max_length=1024)

    @model_validator(mode="after")
    def validate_password_change(self) -> ChangePasswordRequest:
        if self.newPassword != self.confirmPassword:
            raise ValueError("new password and confirmation do not match")
        if self.currentPassword == self.newPassword:
            raise ValueError("new password must be different from current password")
        return self


class NotificationPreferences(BaseModel):
    """Delivery, event, and quiet-hour preferences used by the diagnostics UI."""

    inApp: bool = True
    email: bool = True
    mobile: bool = False
    criticalPatterns: bool = True
    recommendations: bool = True
    validationResults: bool = True
    sourceHealth: bool = True
    weeklyDigest: bool = False
    quietHours: bool = True
    quietStart: str = Field(default="22:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    quietEnd: str = Field(default="07:00", pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class DiagnosticNotificationResponse(BaseModel):
    id: str
    type: Literal["PATTERN", "RECOMMENDATION", "VALIDATION"]
    title: str
    detail: str
    createdAt: str
    href: str
    read: bool


def _hash_password(password: str) -> str:
    """Hash a password with stdlib scrypt and a per-password random salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a password against the versioned scrypt representation."""
    try:
        algorithm, n_raw, r_raw, p_raw, salt_raw, digest_raw = encoded_hash.split("$")
        if algorithm != "scrypt":
            return False
        n, r, p = int(n_raw), int(r_raw), int(p_raw)
        salt = bytes.fromhex(salt_raw)
        expected = bytes.fromhex(digest_raw)
        if (n, r, p) != (2**14, 8, 1) or len(salt) != 16 or len(expected) != 64:
            return False
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p)
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


class InMemoryAccountStore:
    """Thread-safe registration store until the dedicated user-store task lands."""

    def __init__(self) -> None:
        self._users_by_email: dict[str, dict[str, str]] = {}
        self._users_by_id: dict[str, dict[str, str]] = {}
        self._lock = threading.RLock()

    def create(self, *, name: str, email: str, password_hash: str) -> dict[str, str] | None:
        with self._lock:
            if email in self._users_by_email:
                return None
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            user = {
                "id": str(uuid.uuid4()),
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "createdAt": now,
                "role": "Strategy owner",
                "timezone": "UTC",
                "tradingFocus": "XAUUSD intraday",
                "bio": "",
                "joinedAt": now,
                "lastActiveAt": now,
            }
            self._users_by_email[email] = user
            self._users_by_id[user["id"]] = user
            return dict(user)

    def authenticate(self, *, email: str, password: str) -> dict[str, str] | None:
        with self._lock:
            user = self._users_by_email.get(email)
            if user is None or not _verify_password(password, user["password_hash"]):
                return None
            return dict(user)

    def get_profile(self, user_id: str) -> dict[str, str] | None:
        with self._lock:
            user = self._users_by_id.get(user_id)
            return dict(user) if user is not None else None

    def update_profile(self, user_id: str, values: dict[str, str]) -> tuple[str, dict[str, str] | None]:
        with self._lock:
            user = self._users_by_id.get(user_id)
            if user is None:
                return "not_found", None
            email = values["email"]
            email_owner = self._users_by_email.get(email)
            if email_owner is not None and email_owner["id"] != user_id:
                return "email_conflict", None
            previous_email = user["email"]
            user.update(values)
            user["lastActiveAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            if email != previous_email:
                del self._users_by_email[previous_email]
                self._users_by_email[email] = user
            return "updated", dict(user)

    def change_password(self, user_id: str, current_password: str, new_password: str) -> str:
        with self._lock:
            user = self._users_by_id.get(user_id)
            if user is None:
                return "not_found"
            if not _verify_password(current_password, user["password_hash"]):
                return "invalid_password"
            user["password_hash"] = _hash_password(new_password)
            user["lastActiveAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            return "updated"


_account_store = InMemoryAccountStore()


def register_auth_routes(
    app: FastAPI,
    require_auth: AuthDep | None = None,
    account_store: InMemoryAccountStore | None = None,
) -> None:
    """Mount the auth helper routes onto ``app``.

    Args:
        app: The host FastAPI app.
        require_auth: Header-only auth dependency guarding ticket minting. When
            omitted it is resolved from the host ``api_server`` module via
            ``sys.modules`` (matches the other ``register_*_routes`` helpers).
        account_store: Registration repository override used by isolated tests.
    """
    if account_store is None:
        account_store = _account_store

    @app.post(
        "/auth/register",
        response_model=RegisteredUserResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def register_account(payload: RegisterRequest) -> RegisteredUserResponse:
        """Create a local diagnostics account without exposing its password hash."""
        user = account_store.create(
            name=payload.name,
            email=payload.email,
            password_hash=_hash_password(payload.password),
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        return RegisteredUserResponse(**user)

    @app.post("/auth/login", response_model=RegisteredUserResponse)
    async def login(payload: LoginRequest) -> RegisteredUserResponse:
        """Authenticate a local diagnostics account with email and password."""
        user = account_store.authenticate(email=payload.email, password=payload.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return RegisteredUserResponse(**user)

    if require_auth is None:
        import sys as _sys

        host = _sys.modules.get("api_server") or _sys.modules.get("agent.api_server")
        if host is None:  # pragma: no cover — only triggers on weird import setups
            raise RuntimeError(
                "register_auth_routes: api_server module not in sys.modules; "
                "pass require_auth explicitly"
            )
        require_auth = host.require_auth

    def _profile_response(user: dict[str, str] | None) -> UserProfileResponse:
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
        return UserProfileResponse(**user)

    @app.get(
        "/user/profile",
        response_model=UserProfileResponse,
        dependencies=[Depends(require_auth)],
    )
    async def get_user_profile(
        user_id: str = Query(..., min_length=1, max_length=128),
    ) -> UserProfileResponse:
        """Return a user-scoped diagnostics profile."""
        return _profile_response(account_store.get_profile(user_id))

    @app.put(
        "/user/profile",
        response_model=UserProfileResponse,
        dependencies=[Depends(require_auth)],
    )
    async def update_user_profile(
        payload: UpdateUserProfileRequest,
        user_id: str = Query(..., min_length=1, max_length=128),
    ) -> UserProfileResponse:
        """Replace the editable fields of a user-scoped diagnostics profile."""
        result, user = account_store.update_profile(user_id, payload.model_dump())
        if result == "email_conflict":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        return _profile_response(user)

    @app.put(
        "/user/password",
        dependencies=[Depends(require_auth)],
    )
    async def change_user_password(
        payload: ChangePasswordRequest,
        user_id: str = Query(..., min_length=1, max_length=128),
    ) -> dict[str, str]:
        """Replace a user's password after verifying the current credential."""
        result = account_store.change_password(
            user_id,
            current_password=payload.currentPassword,
            new_password=payload.newPassword,
        )
        if result == "not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if result == "invalid_password":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"status": "password_updated"}

    @app.get(
        "/user/notifications",
        response_model=NotificationPreferences,
        dependencies=[Depends(require_auth)],
    )
    async def get_notification_preferences(
        user_id: str = Query(..., min_length=1, max_length=128),
    ) -> NotificationPreferences:
        with DiagnosticsStore() as store:
            preferences = store.notification_preferences(user_id)
        if preferences is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return NotificationPreferences(**preferences)

    @app.put(
        "/user/notifications",
        response_model=NotificationPreferences,
        dependencies=[Depends(require_auth)],
    )
    async def update_notification_preferences(
        payload: NotificationPreferences,
        user_id: str = Query(..., min_length=1, max_length=128),
    ) -> NotificationPreferences:
        with DiagnosticsStore() as store:
            preferences = store.save_notification_preferences(user_id, payload.model_dump())
        if preferences is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return NotificationPreferences(**preferences)

    @app.get(
        "/notifications",
        response_model=list[DiagnosticNotificationResponse],
        dependencies=[Depends(require_auth)],
    )
    async def list_notifications(
        user_id: str = Query(..., min_length=1, max_length=128),
        unread_only: bool = Query(False),
        limit: int = Query(50, ge=1, le=200),
    ) -> list[DiagnosticNotificationResponse]:
        with DiagnosticsStore() as store:
            notifications = store.notifications(
                user_id, unread_only=unread_only, limit=limit,
            )
        if notifications is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return [DiagnosticNotificationResponse(**item) for item in notifications]

    from src.api.security import _mint_sse_ticket

    @app.post("/auth/sse-ticket", dependencies=[Depends(require_auth)])
    async def mint_sse_ticket() -> dict[str, str]:
        """Mint a single-use, ~60s ticket for a browser EventSource connection.

        Gated by the header-only ``require_auth`` dependency, so minting still
        requires the real API key in an ``Authorization`` header — never in a
        URL. The returned ticket replaces the long-lived key in the SSE query
        string and is invalidated on first use.
        """
        return {"ticket": _mint_sse_ticket()}
