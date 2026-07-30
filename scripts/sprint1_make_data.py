"""Build a deterministic XAUUSD H1 series that can produce production entries."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    path = ROOT / ".cache" / "optimization" / "XAUUSD_H1_sprint1.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2023, 1, 2, tzinfo=timezone.utc)
    price = 1900.0
    rows: list[tuple] = []

    def add(bars: int, drift: float, volume: float, wobble: float = 0.0) -> None:
        nonlocal price
        for index in range(bars):
            step = drift + (wobble if index % 2 == 0 else -wobble)
            open_price = price
            close_price = max(1.0, open_price + step)
            high = max(open_price, close_price) + abs(step) * 0.35 + 0.4
            low = min(open_price, close_price) - abs(step) * 0.35 - 0.4
            rows.append((open_price, high, low, close_price, volume))
            price = close_price

    add(220, 0.05, 90.0, 0.02)
    for _ in range(8):
        add(90, 0.45, 180.0, 0.03)
        add(40, -0.08, 70.0, 0.02)
        add(30, 0.20, 95.0, 0.02)
        add(90, -0.45, 180.0, 0.03)
        add(40, 0.08, 70.0, 0.02)
        add(30, -0.20, 95.0, 0.02)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("timestamp", "open", "high", "low", "close", "volume"))
        for index, (o, h, l, c, v) in enumerate(rows):
            ts = (start + timedelta(hours=index)).isoformat()
            writer.writerow((ts, f"{o:.5f}", f"{h:.5f}", f"{l:.5f}", f"{c:.5f}", f"{v:.5f}"))
    print(path, "bars", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
