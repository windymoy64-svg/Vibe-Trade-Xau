"""Analytics orchestration over a replay journal and session."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .performance_metrics import calculate_performance_metrics
from .report_generator import ReportGenerator
from .trade_classifier import AnalyzedTrade, TradeClassifier


@dataclass(frozen=True)
class AnalyticsResult:
    trades: tuple[AnalyzedTrade, ...]
    metrics: dict[str, Any]
    report_paths: dict[str, Path]


class AnalyticsEngine:
    def __init__(self, classifier: TradeClassifier | None = None, reporter: ReportGenerator | None = None) -> None:
        self.classifier = classifier or TradeClassifier()
        self.reporter = reporter or ReportGenerator()

    def analyze(self, journal: object, session: object, output_dir: str | Path = "reports") -> AnalyticsResult:
        source = list(getattr(journal, "trades", ()))
        closed = list(getattr(session, "closed_trades", ()))
        if source and closed and len(source) != len(closed):
            raise ValueError("TradeJournal and ReplaySession closed trade counts disagree")
        trades = tuple(self.classifier.classify(trade) for trade in (source or closed))
        metrics = calculate_performance_metrics(trades, session)
        self._validate(metrics, session, trades)
        paths = self.reporter.generate(trades, metrics, output_dir)
        self._print_summary(trades, metrics)
        return AnalyticsResult(trades=trades, metrics=metrics, report_paths=paths)

    @staticmethod
    def _validate(metrics: dict[str, Any], session: object, trades: tuple[AnalyzedTrade, ...]) -> None:
        if metrics["total_trades"] != len(trades):
            raise RuntimeError("analytics total trade count is inconsistent")
        if metrics["winning_trades"] + metrics["losing_trades"] + metrics["breakeven_trades"] != len(trades):
            raise RuntimeError("analytics outcome counts are inconsistent")
        session_count = int(getattr(session, "trade_count", len(trades)))
        if session_count != len(trades):
            raise ValueError("ReplaySession trade_count disagrees with TradeJournal")
        expected_net = sum(trade.profit for trade in trades)
        if abs(expected_net - metrics["net_profit"]) > 1e-9:
            raise RuntimeError("analytics net profit is inconsistent")

    @staticmethod
    def _print_summary(trades: tuple[AnalyzedTrade, ...], metrics: dict[str, Any]) -> None:
        losses = Counter(trade.outcome_reason for trade in trades if trade.profit < 0)
        wins = Counter(trade.outcome_reason for trade in trades if trade.profit > 0)
        loss_reason = losses.most_common(1)[0][0] if losses else "None"
        win_reason = wins.most_common(1)[0][0] if wins else "None"
        factor = metrics["profit_factor"]
        factor_text = "Infinity" if factor == float("inf") else f"{factor:.2f}"
        print(
            "Replay Analysis Complete\n"
            f"Trades: {metrics['total_trades']}\n"
            f"Win Rate: {metrics['win_rate']:.1%}\n"
            f"Profit Factor: {factor_text}\n"
            f"Expectancy: {metrics['expectancy']:.2f}R\n"
            f"Most Common Loss Reason: {loss_reason}\n"
            f"Most Common Win Reason: {win_reason}"
        )
