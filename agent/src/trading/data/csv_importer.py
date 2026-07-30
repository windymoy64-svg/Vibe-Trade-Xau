"""Standard OHLCV CSV parser."""

from __future__ import annotations
import csv
from pathlib import Path


class CSVImporter:
    source_format = "standard_csv"
    required = ("timestamp", "open", "high", "low", "close", "volume")

    def read(self, path):
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            names = {str(name).strip().lower(): name for name in (reader.fieldnames or ())}
            missing = set(self.required) - set(names)
            if missing:
                raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")
            return [{key: row[names[key]].strip() for key in self.required} for row in reader]
