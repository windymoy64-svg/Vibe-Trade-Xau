from datetime import datetime, timezone

import pytest

from src.trading.analytics import AnalyticsEngine, TradeClassifier, calculate_performance_metrics
from src.trading.replay.replay_session import ReplaySession
from src.trading.replay.trade_journal import TradeJournal, TradeRecord


def _trade(trade_id, profit, r_multiple, close_reason="TP", confidence=0.8, reasons=("EMA_TREND",)):
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return TradeRecord(
        trade_id=trade_id,
        symbol="XAUUSD",
        entry_time=now,
        exit_time=now,
        entry_price=2000,
        exit_price=2010 if profit > 0 else 1990,
        side="LONG",
        volume=1,
        sl=1990,
        tp=2020,
        profit=profit,
        r_multiple=r_multiple,
        holding_candles=3,
        close_reason=close_reason,
        signal={"confidence": confidence, "reason_codes": reasons},
        decision={"action": "OPEN_LONG", "reason_codes": reasons},
    )


def test_classifier_uses_explainable_recorded_state():
    analyzed = TradeClassifier().classify(_trade("1", -100, -1, "SL"))
    assert analyzed.trade_label == "Trend Following"
    assert analyzed.outcome_reason == "Stopped Out"
    assert analyzed.risk_approval == "APPROVED"
    assert analyzed.confidence == 0.8


def test_metrics_and_reports_are_consistent(tmp_path):
    trades = [_trade("1", 200, 2), _trade("2", -100, -1, "SL"), _trade("3", 100, 1)]
    journal = TradeJournal()
    journal.trades.extend(trades)
    session = ReplaySession()
    session.closed_trades.extend(trades)
    session.trade_count = 3
    session.equity_history = [(None, 10000), (None, 10200), (None, 10100), (None, 10200)]
    result = AnalyticsEngine().analyze(journal, session, tmp_path)
    assert result.metrics["win_rate"] == pytest.approx(2 / 3)
    assert result.metrics["profit_factor"] == 3
    assert result.metrics["maximum_drawdown"] == 100
    assert result.metrics["recovery_factor"] == 2
    assert all(path.exists() for path in result.report_paths.values())


def test_empty_metrics_are_finite_and_reportable(tmp_path):
    session = ReplaySession()
    metrics = calculate_performance_metrics([], session)
    assert metrics["total_trades"] == 0 and metrics["profit_factor"] == 0
    result = AnalyticsEngine().analyze(TradeJournal(), session, tmp_path)
    assert len(result.report_paths) == 4


def test_all_winners_produce_strict_json(tmp_path):
    trade = _trade("1", 100, 1)
    journal = TradeJournal()
    journal.trades.append(trade)
    session = ReplaySession()
    session.closed_trades.append(trade)
    session.trade_count = 1
    result = AnalyticsEngine().analyze(journal, session, tmp_path)
    assert result.metrics["profit_factor"] == float("inf")
    assert '"profit_factor": "Infinity"' in (tmp_path / "performance.json").read_text(encoding="utf-8")
