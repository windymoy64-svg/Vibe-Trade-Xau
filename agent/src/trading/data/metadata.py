"""Historical dataset metadata contracts."""

from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    message: str
    rows: tuple[int, ...] = ()


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    input_rows: int
    output_rows: int
    issues: tuple[ValidationIssue, ...]

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class DatasetMetadata:
    symbol: str
    timeframe: str
    start: datetime
    end: datetime
    candles: int
    checksum: str
    source_format: str
    processed_csv: str
    validation: ValidationReport

    def as_dict(self):
        return asdict(self)
