"""Deterministic normalization without candle fabrication."""


class DatasetCleaner:
    def clean(self, rows):
        # Last duplicate is retained deterministically; no missing bars are synthesized.
        by_time = {row["timestamp"]: row for row in rows}
        return [by_time[key] for key in sorted(by_time)]
