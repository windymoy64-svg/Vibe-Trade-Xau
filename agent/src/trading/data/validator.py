"""Fail-closed historical candle validation and interval diagnostics."""

from __future__ import annotations
import math
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from .metadata import ValidationIssue, ValidationReport


class DatasetValidationError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__("dataset contains unsafe market-data errors")


class DatasetValidator:
    def validate(self, rows, timeframe):
        issues = []
        parsed = []
        timezone_kinds = set()
        invalid = []
        for index, row in enumerate(rows, 2):
            try:
                timestamp, kind = _timestamp(row["timestamp"])
                timezone_kinds.add(kind)
                values = {key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}
                if not all(math.isfinite(value) for value in values.values()):
                    raise ValueError("non-finite value")
                if values["volume"] < 0:
                    raise ValueError("negative volume")
                if min(values[k] for k in ("open", "high", "low", "close")) <= 0:
                    raise ValueError("non-positive price")
                if values["high"] < max(values["open"], values["close"], values["low"]):
                    raise ValueError("invalid high")
                if values["low"] > min(values["open"], values["close"], values["high"]):
                    raise ValueError("invalid low")
                parsed.append({"timestamp": timestamp, **values, "source_row": index})
            except (KeyError, TypeError, ValueError) as exc:
                invalid.append(index)
                issues.append(ValidationIssue("INVALID_ROW", "error", f"row {index}: {exc}", (index,)))
        if len(timezone_kinds) > 1:
            issues.append(ValidationIssue("TIMEZONE_INCONSISTENT", "error", "mixed aware and naive timestamps"))
        timestamps = [row["timestamp"] for row in parsed]
        duplicates = tuple(sorted({row["source_row"] for row in parsed if Counter(timestamps)[row["timestamp"]] > 1}))
        if duplicates:
            issues.append(
                ValidationIssue("DUPLICATE_TIMESTAMPS", "warning", f"{len(duplicates)} duplicate rows", duplicates)
            )
        if any(left > right for left, right in zip(timestamps, timestamps[1:])):
            issues.append(ValidationIssue("OUT_OF_ORDER", "warning", "candles are not chronological"))
        unique = sorted(set(timestamps))
        interval = _duration(timeframe)
        gaps = [
            (left, right, int((right - left) / interval) - 1)
            for left, right in zip(unique, unique[1:])
            if right - left > interval
        ]
        if gaps:
            count = sum(gap[2] for gap in gaps)
            issues.append(
                ValidationIssue("MISSING_TIMESTAMPS", "warning", f"{count} expected candle timestamps are missing")
            )
        report = ValidationReport(not invalid and len(timezone_kinds) <= 1, len(rows), len(parsed), tuple(issues))
        if not report.valid:
            raise DatasetValidationError(report)
        return parsed, report


def _timestamp(value):
    text = str(value).strip().replace("Z", "+00:00")
    parsed = None
    for candidate in (text, text.replace(".", "-").replace(" ", "T", 1)):
        try:
            parsed = datetime.fromisoformat(candidate)
            break
        except ValueError:
            pass
    if parsed is None:
        raise ValueError("invalid timestamp")
    kind = "naive" if parsed.tzinfo is None else "aware"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc), kind


def _duration(value):
    match = re.fullmatch(r"(\d+)([mhdwM])", value)
    if not match:
        raise ValueError(f"unsupported timeframe: {value}")
    amount = int(match.group(1))
    unit = match.group(2)
    return {
        "m": timedelta(minutes=amount),
        "h": timedelta(hours=amount),
        "d": timedelta(days=amount),
        "w": timedelta(weeks=amount),
        "M": timedelta(days=30 * amount),
    }[unit]
