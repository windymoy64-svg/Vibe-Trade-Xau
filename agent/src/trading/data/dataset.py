"""Import, validate, clean, checksum, and persist replay-ready datasets."""

from __future__ import annotations
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from .cleaner import DatasetCleaner
from .csv_importer import CSVImporter
from .metadata import DatasetMetadata, ValidationReport
from .mt5_importer import MT5CSVImporter
from .validator import DatasetValidator


class HistoricalDataset:
    def __init__(self, validator=None, cleaner=None):
        self.validator = validator or DatasetValidator()
        self.cleaner = cleaner or DatasetCleaner()

    def import_file(self, path, *, symbol=None, timeframe=None, output_dir=None, source_format="auto"):
        source = Path(path)
        symbol = (symbol or _symbol(source)).upper()
        timeframe = timeframe or _timeframe(source)
        importer = self._importer(source, source_format)
        raw = importer.read(source)
        validated, initial = self.validator.validate(raw, timeframe)
        cleaned = self.cleaner.clean(validated)
        # Revalidate output to guarantee replay's strict chronological contract.
        normalized = [
            {k: (v.isoformat() if k == "timestamp" else v) for k, v in row.items() if k != "source_row"}
            for row in cleaned
        ]
        _, final = self.validator.validate(normalized, timeframe)
        report = ValidationReport(True, initial.input_rows, len(cleaned), initial.issues + final.issues)
        destination = Path(output_dir) if output_dir else source.parent / (source.stem + "_dataset")
        destination.mkdir(parents=True, exist_ok=True)
        csv_path = destination / "processed.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=("timestamp", "open", "high", "low", "close", "volume"), lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(normalized)
        checksum = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        metadata = DatasetMetadata(
            symbol,
            timeframe,
            cleaned[0]["timestamp"],
            cleaned[-1]["timestamp"],
            len(cleaned),
            checksum,
            importer.source_format,
            csv_path.name,
            report,
        )
        (destination / "dataset.json").write_text(
            json.dumps(asdict(metadata), default=_json, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return csv_path, metadata

    @staticmethod
    def _importer(path, source_format):
        if source_format == "standard":
            return CSVImporter()
        if source_format == "mt5":
            return MT5CSVImporter()
        try:
            CSVImporter().read(path)
            return CSVImporter()
        except ValueError:
            return MT5CSVImporter()


def _symbol(path):
    return path.stem.split("_")[0] or "UNKNOWN"


def _timeframe(path):
    token = next((part for part in path.stem.upper().split("_") if part[:1] in "MHDW" and part[1:].isdigit()), None)
    if not token:
        raise ValueError("timeframe is required when it cannot be inferred from filename")
    return token[1:] + {"M": "m", "H": "h", "D": "d", "W": "w"}[token[0]]


def _json(value):
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
