"""Import a standard or MetaTrader5 CSV into a validated replay dataset."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
from src.trading.data import DatasetValidationError, HistoricalDataset  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--symbol")
    parser.add_argument("--timeframe")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=("auto", "standard", "mt5"), default="auto")
    args = parser.parse_args()
    try:
        csv_path, metadata = HistoricalDataset().import_file(
            args.csv, symbol=args.symbol, timeframe=args.timeframe, output_dir=args.output, source_format=args.format
        )
    except DatasetValidationError as exc:
        print("Dataset Import Failed", file=sys.stderr)
        for issue in exc.report.issues:
            print(f"{issue.severity.upper()}: {issue.code}: {issue.message}", file=sys.stderr)
        return 2
    print(f"Dataset Import Complete\nCSV: {csv_path}\nCandles: {metadata.candles}\nChecksum: {metadata.checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
