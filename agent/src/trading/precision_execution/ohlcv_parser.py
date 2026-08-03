"""Strict, bounded parsing for user-supplied OHLCV CSV and JSON files."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path

from src.trading.auto_selection import OHLCVBar


class OHLCVParseError(ValueError):
    pass


class OHLCVFileParser:
    def __init__(self, *, maximum_bytes: int = 5 * 1024 * 1024, maximum_rows: int = 100_000) -> None:
        if maximum_bytes <= 0 or maximum_rows <= 0:
            raise ValueError("parser limits must be positive")
        self.maximum_bytes = maximum_bytes
        self.maximum_rows = maximum_rows

    def parse(self, filename: str, content: bytes) -> tuple[OHLCVBar, ...]:
        suffix = Path(filename or "").suffix.lower()
        if suffix not in {".csv", ".json"}:
            raise OHLCVParseError("only .csv and .json OHLCV files are supported")
        if not content:
            raise OHLCVParseError("OHLCV file is empty")
        if len(content) > self.maximum_bytes:
            raise OHLCVParseError("OHLCV file exceeds the size limit")
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise OHLCVParseError("OHLCV file must use UTF-8 encoding") from exc
        rows = self._csv_rows(text) if suffix == ".csv" else self._json_rows(text)
        if not rows:
            raise OHLCVParseError("OHLCV file contains no candles")
        if len(rows) > self.maximum_rows:
            raise OHLCVParseError("OHLCV file exceeds the row limit")

        bars: list[OHLCVBar] = []
        previous: datetime | None = None
        for index, row in enumerate(rows, start=1):
            try:
                bar = _bar(row)
            except (KeyError, TypeError, ValueError) as exc:
                raise OHLCVParseError(f"row {index}: {exc}") from exc
            if previous is not None and bar.timestamp <= previous:
                raise OHLCVParseError(f"row {index}: timestamps must be unique and ascending")
            previous = bar.timestamp
            bars.append(bar)
        return tuple(bars)

    @staticmethod
    def _csv_rows(text: str) -> list[dict[str, object]]:
        try:
            reader = csv.DictReader(io.StringIO(text, newline=""))
            headers = {str(header or "").strip().lower() for header in (reader.fieldnames or [])}
            required = {"timestamp", "open", "high", "low", "close", "volume"}
            if not required <= headers:
                raise OHLCVParseError("CSV requires timestamp, open, high, low, close, volume headers")
            return [
                {str(key).strip().lower(): value for key, value in row.items() if key is not None}
                for row in reader
            ]
        except csv.Error as exc:
            raise OHLCVParseError("invalid OHLCV CSV") from exc

    @staticmethod
    def _json_rows(text: str) -> list[dict[str, object]]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise OHLCVParseError("invalid OHLCV JSON") from exc
        if isinstance(payload, dict):
            payload = payload.get("candles")
        if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
            raise OHLCVParseError("JSON must be an array of candle objects or contain a candles array")
        return [{str(key).strip().lower(): value for key, value in row.items()} for row in payload]


def _bar(row: dict[str, object]) -> OHLCVBar:
    raw_timestamp = str(row["timestamp"]).strip()
    timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return OHLCVBar(
        timestamp=timestamp,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
    )
