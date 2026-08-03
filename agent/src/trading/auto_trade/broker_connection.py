"""Decrypt stored credentials only for a bounded broker connection check."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol

from .credential_encryption import BrokerCredentialEncryptionService


class EncryptedCredentialSource(Protocol):
    def get_encrypted_api_credential(
        self, user_id: str, provider: str,
    ) -> dict[str, object] | None: ...


@dataclass(frozen=True, slots=True)
class BrokerConnectionVerification:
    provider: str
    status: Literal["CONNECTED", "ERROR"]
    last_four: str
    message: str
    checked_at: str


class BrokerCredentialNotFoundError(ValueError):
    pass


class BrokerConnectionVerificationService:
    """Verify one encrypted credential without returning decrypted material."""

    def __init__(
        self,
        source: EncryptedCredentialSource,
        encryption: BrokerCredentialEncryptionService,
        verifier: Callable[[str, str], bool],
    ) -> None:
        self._source = source
        self._encryption = encryption
        self._verifier = verifier

    def verify(self, user_id: str, provider: str) -> BrokerConnectionVerification:
        normalized_provider = provider.strip()
        credential = self._source.get_encrypted_api_credential(user_id, normalized_provider)
        if credential is None:
            raise BrokerCredentialNotFoundError("broker credential not found")
        api_key = self._encryption.decrypt(
            credential["ciphertext"],  # type: ignore[arg-type]
            credential["nonce"],  # type: ignore[arg-type]
            user_id=user_id,
            provider=normalized_provider,
        )
        try:
            connected = bool(self._verifier(normalized_provider, api_key))
            message = "Broker connection verified." if connected else "Broker rejected the credential."
        except Exception:
            connected = False
            message = "Broker connection verification failed."
        finally:
            api_key = ""
        return BrokerConnectionVerification(
            provider=normalized_provider,
            status="CONNECTED" if connected else "ERROR",
            last_four=str(credential["lastFour"]),
            message=message,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
