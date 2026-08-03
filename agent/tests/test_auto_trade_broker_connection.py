import os

import pytest

from src.trading.auto_trade import (
    BrokerConnectionVerificationService,
    BrokerCredentialEncryptionService,
    BrokerCredentialNotFoundError,
)


class Source:
    def __init__(self, credential):
        self.credential = credential

    def get_encrypted_api_credential(self, user_id, provider):
        return self.credential if (user_id, provider) == ("alice", "MT5") else None


def _service(verifier):
    encryption = BrokerCredentialEncryptionService(os.urandom(32))
    encrypted = encryption.encrypt("broker-secret-A1B2", user_id="alice", provider="MT5")
    source = Source({
        "provider": "MT5", "ciphertext": encrypted.ciphertext,
        "nonce": encrypted.nonce, "keyVersion": 1, "lastFour": "A1B2",
    })
    return BrokerConnectionVerificationService(source, encryption, verifier)


def test_connection_verifier_receives_decrypted_key_but_result_does_not_expose_it():
    calls = []
    service = _service(lambda provider, api_key: calls.append((provider, api_key)) or True)

    result = service.verify("alice", "MT5")

    assert calls == [("MT5", "broker-secret-A1B2")]
    assert result.status == "CONNECTED"
    assert result.last_four == "A1B2"
    assert "broker-secret" not in repr(result)


def test_connection_rejection_and_transport_error_are_normalized():
    rejected = _service(lambda provider, api_key: False).verify("alice", "MT5")
    failed = _service(
        lambda provider, api_key: (_ for _ in ()).throw(TimeoutError("broker timeout")),
    ).verify("alice", "MT5")

    assert rejected.status == "ERROR"
    assert "rejected" in rejected.message
    assert failed.status == "ERROR"
    assert failed.message == "Broker connection verification failed."


def test_connection_verification_is_user_scoped():
    with pytest.raises(BrokerCredentialNotFoundError):
        _service(lambda provider, api_key: True).verify("bob", "MT5")
