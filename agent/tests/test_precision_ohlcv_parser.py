import json

import pytest

from src.trading.precision_execution import OHLCVFileParser, OHLCVParseError


CSV = b"""timestamp,open,high,low,close,volume
2026-08-01T08:00:00Z,2380,2386,2379,2384,100
2026-08-01T08:15:00Z,2384,2391,2383,2389,120
"""


def test_parser_reads_strict_csv_and_json_without_persisting():
    parser = OHLCVFileParser()
    csv_bars = parser.parse("xauusd.csv", CSV)
    json_bars = parser.parse("xauusd.json", json.dumps({"candles": [
        {"timestamp": "2026-08-01T08:00:00Z", "open": 2380, "high": 2386,
         "low": 2379, "close": 2384, "volume": 100},
    ]}).encode())

    assert len(csv_bars) == 2
    assert csv_bars[1].close == 2389
    assert json_bars[0].timestamp.isoformat() == "2026-08-01T08:00:00+00:00"


@pytest.mark.parametrize("filename,content,message", [
    ("data.txt", CSV, "only"),
    ("data.csv", b"timestamp,open\n", "requires"),
    ("data.json", b"not-json", "invalid"),
    ("data.json", b"[]", "no candles"),
])
def test_parser_rejects_unsupported_or_malformed_files(filename, content, message):
    with pytest.raises(OHLCVParseError, match=message):
        OHLCVFileParser().parse(filename, content)


def test_parser_rejects_naive_duplicate_and_invalid_candles():
    parser = OHLCVFileParser()
    with pytest.raises(OHLCVParseError, match="timezone"):
        parser.parse("data.csv", CSV.replace(b"Z,2380", b",2380", 1))
    with pytest.raises(OHLCVParseError, match="unique"):
        parser.parse("data.csv", CSV.replace(b"08:15:00", b"08:00:00"))
    with pytest.raises(OHLCVParseError, match="range"):
        parser.parse("data.csv", CSV.replace(b"2386,2379", b"2378,2379", 1))


def test_parser_enforces_file_and_row_limits():
    with pytest.raises(OHLCVParseError, match="size"):
        OHLCVFileParser(maximum_bytes=10).parse("data.csv", CSV)
    with pytest.raises(OHLCVParseError, match="row"):
        OHLCVFileParser(maximum_rows=1).parse("data.csv", CSV)
