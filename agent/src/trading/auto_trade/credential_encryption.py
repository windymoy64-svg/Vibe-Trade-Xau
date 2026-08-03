"""Authenticated encryption for persisted broker API credentials."""

from __future__ import annotations

import base64
import binascii
import os
import re
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MASTER_KEY_ENV = "VIBE_TRADING_CREDENTIAL_ENCRYPTION_KEY"
_NONCE_BYTES = 12


class CredentialEncryptionConfigurationError(RuntimeError):
    """Raised when the credential master key is unavailable or malformed."""


@dataclass(frozen=True, slots=True)
class EncryptedCredential:
    ciphertext: bytes
    nonce: bytes


class BrokerCredentialEncryptionService:
    """Encrypt broker credentials with user/provider-bound associated data."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) != 32:
            raise CredentialEncryptionConfigurationError(
                "Credential encryption key must decode to exactly 32 bytes"
            )
        self._cipher = AESGCM(master_key)

    @classmethod
    def from_environment(cls) -> BrokerCredentialEncryptionService:
        encoded_key = os.getenv(_MASTER_KEY_ENV)
        if not encoded_key:
            raise CredentialEncryptionConfigurationError(
                f"{_MASTER_KEY_ENV} is not configured"
            )
        if re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", encoded_key) is None:
            raise CredentialEncryptionConfigurationError(
                f"{_MASTER_KEY_ENV} must be valid urlsafe base64"
            )
        try:
            master_key = base64.b64decode(
                encoded_key.encode("ascii"), altchars=b"-_", validate=True
            )
        except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
            raise CredentialEncryptionConfigurationError(
                f"{_MASTER_KEY_ENV} must be valid urlsafe base64"
            ) from exc
        return cls(master_key)

    @staticmethod
    def _associated_data(user_id: str, provider: str) -> bytes:
        return f"{user_id}\0{provider}".encode("utf-8")

    def encrypt(
        self, api_key: str, *, user_id: str, provider: str,
    ) -> EncryptedCredential:
        nonce = os.urandom(_NONCE_BYTES)
        ciphertext = self._cipher.encrypt(
            nonce,
            api_key.encode("utf-8"),
            self._associated_data(user_id, provider),
        )
        return EncryptedCredential(ciphertext=ciphertext, nonce=nonce)

    def decrypt(
        self,
        ciphertext: bytes,
        nonce: bytes,
        *,
        user_id: str,
        provider: str,
    ) -> str:
        plaintext = self._cipher.decrypt(
            nonce, ciphertext, self._associated_data(user_id, provider)
        )
        return plaintext.decode("utf-8")
