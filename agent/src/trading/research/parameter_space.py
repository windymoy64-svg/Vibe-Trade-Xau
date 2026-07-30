"""Stable Cartesian parameter-space generation."""

from __future__ import annotations

from itertools import product
from typing import Any, Iterator, Mapping, Sequence


class ParameterSpace:
    """An immutable grid whose combinations follow definition/value order."""

    def __init__(self, definitions: Mapping[str, Sequence[Any]]) -> None:
        if not definitions:
            raise ValueError("parameter space must not be empty")
        self._definitions = tuple((str(name), tuple(values)) for name, values in definitions.items())
        for name, values in self._definitions:
            if not name.strip():
                raise ValueError("parameter names must not be empty")
            if not values:
                raise ValueError(f"parameter {name!r} has no values")

    def combinations(self) -> Iterator[dict[str, Any]]:
        names = tuple(name for name, _ in self._definitions)
        values = tuple(options for _, options in self._definitions)
        for combination in product(*values):
            yield dict(zip(names, combination, strict=True))

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return self.combinations()

    def __len__(self) -> int:
        size = 1
        for _, values in self._definitions:
            size *= len(values)
        return size

    @property
    def definitions(self) -> dict[str, tuple[Any, ...]]:
        return dict(self._definitions)
