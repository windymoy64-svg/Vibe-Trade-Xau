"""MetaTrader 5 bar-history CSV export parser."""

from __future__ import annotations
import csv
from pathlib import Path


class MT5CSVImporter:
    source_format = "mt5_csv"

    def read(self, path):
        with Path(path).open(newline="", encoding="utf-8-sig") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            delimiter = "\t" if sample.count("\t") > sample.count(",") else ","
            reader = csv.DictReader(handle, delimiter=delimiter)
            fields = {_name(name): name for name in (reader.fieldnames or ())}
            required = {"date", "time", "open", "high", "low", "close"}
            if not required <= fields.keys():
                raise ValueError("not a supported MetaTrader5 CSV export")
            volume = fields.get("tickvol") or fields.get("vol") or fields.get("realvolume")
            if volume is None:
                raise ValueError("MT5 CSV export has no volume column")
            return [
                {
                    "timestamp": f"{row[fields['date']].strip()} {row[fields['time']].strip()}",
                    "open": row[fields["open"]].strip(),
                    "high": row[fields["high"]].strip(),
                    "low": row[fields["low"]].strip(),
                    "close": row[fields["close"]].strip(),
                    "volume": row[volume].strip(),
                }
                for row in reader
            ]


def _name(value):
    return str(value).strip().strip("<>").lower().replace("_", "").replace(" ", "")
