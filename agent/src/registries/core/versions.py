"""Strict semantic versions without a third-party versioning dependency."""

from __future__ import annotations

import re
from functools import total_ordering
from typing import Any

from pydantic_core import core_schema

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@total_ordering
class SemanticVersion(str):
    """Validated SemVer 2.0 value with deterministic precedence ordering."""

    def __new__(cls, value: str) -> "SemanticVersion":
        if not isinstance(value, str) or not _SEMVER_RE.fullmatch(value.strip()):
            raise ValueError(f"invalid semantic version: {value!r}")
        return str.__new__(cls, value.strip())

    @property
    def _parts(self) -> tuple[int, int, int, tuple[tuple[int, int | str], ...] | None]:
        match = _SEMVER_RE.fullmatch(self)
        assert match is not None
        prerelease = match.group(4)
        pre_key = None
        if prerelease is not None:
            pre_key = tuple(
                (0, int(item)) if item.isdigit() else (1, item)
                for item in prerelease.split(".")
            )
        return int(match.group(1)), int(match.group(2)), int(match.group(3)), pre_key

    @property
    def major(self) -> int:
        return self._parts[0]

    @property
    def minor(self) -> int:
        return self._parts[1]

    @property
    def patch(self) -> int:
        return self._parts[2]

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, (str, SemanticVersion)):
            return NotImplemented
        other_version = SemanticVersion(str(other))
        left = self._parts
        right = other_version._parts
        if left[:3] != right[:3]:
            return left[:3] < right[:3]
        if left[3] is None:
            return False if right[3] is None else False
        if right[3] is None:
            return True
        return left[3] < right[3]

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: Any, _handler: Any) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())
