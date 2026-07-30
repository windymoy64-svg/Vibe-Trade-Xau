import hashlib
import json
import pytest
from src.trading.data import DatasetValidationError, HistoricalDataset
from src.trading.replay.candle_feed import CandleFeed


def test_standard_import_cleans_duplicates_order_and_reports_gap(tmp_path):
    raw = tmp_path / "XAUUSD_H1.csv"
    raw.write_text(
        "timestamp,open,high,low,close,volume\n2024-01-01T02:00:00Z,2,3,1,2.5,10\n"
        "2024-01-01T00:00:00Z,1,2,0.5,1.5,8\n2024-01-01T02:00:00Z,2,3,1,2.6,11\n",
        encoding="utf-8",
    )
    csv_path, metadata = HistoricalDataset().import_file(raw, output_dir=tmp_path / "out")
    assert metadata.candles == 2 and metadata.symbol == "XAUUSD" and metadata.timeframe == "1h"
    assert {issue.code for issue in metadata.validation.issues} >= {
        "DUPLICATE_TIMESTAMPS",
        "OUT_OF_ORDER",
        "MISSING_TIMESTAMPS",
    }
    assert metadata.checksum == hashlib.sha256(csv_path.read_bytes()).hexdigest()
    feed = CandleFeed.from_csv(csv_path, symbol=metadata.symbol, timeframe=metadata.timeframe)
    assert feed.length() == 2 and feed.next().timestamp < feed.next().timestamp


def test_mt5_export_import(tmp_path):
    raw = tmp_path / "XAUUSD_H1.csv"
    raw.write_text(
        "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
        "2024.01.01\t00:00:00\t2000\t2002\t1999\t2001\t100\t0\t20\n",
        encoding="utf-8",
    )
    csv_path, metadata = HistoricalDataset().import_file(raw, output_dir=tmp_path / "mt5")
    assert metadata.source_format == "mt5_csv" and metadata.candles == 1
    assert json.loads((tmp_path / "mt5" / "dataset.json").read_text())["symbol"] == "XAUUSD"
    assert csv_path.exists()


@pytest.mark.parametrize("row", ["2024-01-01T00:00:00Z,2,1,0.5,1.5,10", "2024-01-01T00:00:00Z,1,2,.5,1.5,-1"])
def test_unsafe_market_rows_fail_closed(tmp_path, row):
    raw = tmp_path / "XAUUSD_H1.csv"
    raw.write_text("timestamp,open,high,low,close,volume\n" + row + "\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError):
        HistoricalDataset().import_file(raw)
