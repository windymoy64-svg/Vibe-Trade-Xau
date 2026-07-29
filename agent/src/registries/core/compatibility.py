"""Deterministic compatibility checks for generic registry records."""

from __future__ import annotations

from src.aios.contracts.environment import ExecutionEnvironment
from src.registries.core.errors import IncompatibleRecordError
from src.registries.core.records import RegistryRecord
from src.registries.core.versions import SemanticVersion


def validate_record_compatibility(
    record: RegistryRecord,
    *,
    environment: ExecutionEnvironment,
    api_version: SemanticVersion,
) -> None:
    """Raise when a record does not declare compatibility with the request."""
    spec = record.compatibility
    if environment not in spec.supported_environments:
        raise IncompatibleRecordError(
            f"{record.key} does not support environment {environment.value}"
        )
    try:
        required_api = SemanticVersion(spec.api_version)
    except ValueError as exc:
        raise IncompatibleRecordError(
            f"{record.key} declares invalid api_version {spec.api_version!r}"
        ) from exc
    if required_api.major != api_version.major:
        raise IncompatibleRecordError(
            f"{record.key} requires API major {required_api.major}, got {api_version.major}"
        )
