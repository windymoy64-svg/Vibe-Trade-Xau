"""CSV, JSON, and plain-text analytics report generation."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


class ReportGenerator:
    FILENAMES = ("trade_summary.csv", "trade_details.csv", "performance.json", "analytics_summary.txt")

    def generate(
        self, trades: Iterable[object], metrics: dict[str, Any], output_dir: str | Path = "reports"
    ) -> dict[str, Path]:
        rows = [trade.as_dict() for trade in trades]
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        paths = {name: directory / name for name in self.FILENAMES}
        self._write_summary_csv(paths["trade_summary.csv"], rows)
        self._write_details_csv(paths["trade_details.csv"], rows)
        paths["performance.json"].write_text(
            json.dumps(_strict_json(metrics), indent=2, sort_keys=True, allow_nan=False, default=_json_value) + "\n",
            encoding="utf-8",
        )
        paths["analytics_summary.txt"].write_text(self.summary_text(rows, metrics), encoding="utf-8")
        return paths

    @staticmethod
    def summary_text(rows: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
        loss_reason, loss_count = _common_reason(rows, losing=True)
        win_reason, win_count = _common_reason(rows, losing=False)
        return (
            "Replay Summary\n\n"
            f"Trades\n{metrics['total_trades']}\n\n"
            f"Win Rate\n{metrics['win_rate']:.1%}\n\n"
            f"Profit Factor\n{_display(metrics['profit_factor'])}\n\n"
            f"Expectancy\n{metrics['expectancy']:.2f}R\n\n"
            f"Largest Win\n{metrics['largest_win']:.2f}\n\n"
            f"Largest Loss\n{metrics['largest_loss']:.2f}\n\n"
            f"Most Common Loss Reason\n{loss_reason}\n{loss_count}\n\n"
            f"Most Common Win Reason\n{win_reason}\n{win_count}\n"
        )

    @staticmethod
    def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        fields = ["trade_id", "symbol", "side", "profit", "r_multiple", "trade_label", "outcome_reason"]
        _write_csv(path, fields, rows)

    @staticmethod
    def _write_details_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        fields = [
            "trade_id",
            "symbol",
            "side",
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
            "holding_candles",
            "profit",
            "r_multiple",
            "signal",
            "decision",
            "risk_approval",
            "volume",
            "sl",
            "tp",
            "confidence",
            "replay_timestamp",
            "trade_label",
            "outcome_reason",
            "close_reason",
        ]
        _write_csv(path, fields, rows)


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fields})


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=_json_value)
    return _json_value(value)


def _json_value(value: Any) -> Any:
    if isinstance(value, float) and math.isinf(value):
        return "Infinity"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _strict_json(value: Any) -> Any:
    """Convert non-finite ratios to explicit strings for standards-compliant JSON."""
    if isinstance(value, dict):
        return {key: _strict_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_strict_json(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity"
    return value


def _common_reason(rows: list[dict[str, Any]], *, losing: bool) -> tuple[str, int]:
    reasons = Counter(
        str(row["outcome_reason"]) for row in rows if (float(row["profit"]) < 0 if losing else float(row["profit"]) > 0)
    )
    return reasons.most_common(1)[0] if reasons else ("None", 0)


def _display(value: float) -> str:
    return "Infinity" if math.isinf(value) else f"{value:.2f}"
