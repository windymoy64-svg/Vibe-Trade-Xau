"""Explicit registry failure types; failures are never silently downgraded."""


class RegistryError(RuntimeError):
    """Base registry failure."""


class DuplicateRecordError(RegistryError):
    """Raised when an immutable registry key already exists."""


class RecordNotFoundError(RegistryError):
    """Raised when a requested registry record does not exist."""


class IncompatibleRecordError(RegistryError):
    """Raised when compatibility requirements cannot be satisfied."""


class CorruptRegistryError(RegistryError):
    """Raised when persisted registry state exists but cannot be trusted."""

    def __init__(self, path: str, cause: str) -> None:
        super().__init__(f"registry file {path} is corrupt: {cause}")
        self.path = path
        self.cause = cause
