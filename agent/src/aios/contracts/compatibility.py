"""Storage-independent compatibility declarations."""

from __future__ import annotations

from pydantic import Field, model_validator

from src.aios.contracts.environment import ExecutionEnvironment
from src.aios.contracts.identifiers import FrozenContract


class VersionRange(FrozenContract):
    """Inclusive lower and exclusive upper semantic-version bounds."""

    minimum: str | None = None
    maximum_exclusive: str | None = None


class CompatibilitySpec(FrozenContract):
    """Declared compatibility independent of any concrete registry backend."""

    api_version: str
    schema_version: int = Field(default=1, gt=0)
    python_requires: VersionRange | None = None
    supported_environments: tuple[ExecutionEnvironment, ...] = (
        ExecutionEnvironment.RESEARCH,
    )
    requires: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_unique_values(self) -> "CompatibilitySpec":
        if not self.supported_environments:
            raise ValueError("supported_environments cannot be empty")
        if len(set(self.supported_environments)) != len(self.supported_environments):
            raise ValueError("supported_environments must be unique")
        if len(set(self.requires)) != len(self.requires):
            raise ValueError("requires must be unique")
        return self
