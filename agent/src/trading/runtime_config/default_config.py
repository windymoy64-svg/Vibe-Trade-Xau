"""Canonical defaults reproducing the pre-injection production behavior."""

from types import MappingProxyType

from .runtime_config import RuntimeConfig

DEFAULT_CONFIG = MappingProxyType(RuntimeConfig().model_dump(by_alias=True))


def default_runtime_config() -> RuntimeConfig:
    return RuntimeConfig()
