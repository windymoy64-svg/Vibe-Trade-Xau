"""Tests for automatic loss-pattern detection and persistence."""

from __future__ import annotations

import pytest

from src.diagnostics.pattern_service import LossPatternDetectionService
from src.diagnostics.store import DiagnosticsStore


def _insert_trade(store: DiagnosticsStore, trade_id: str, user_id: str, **overrides: object) -> None:
    values = {
        "direction": "BUY", "trend_status": "BULLISH", "ema_alignment": "BULLISH",
        "rsi_value": 60, "volume_status": "NORMAL", "market_regime": "TRENDING",
        "trading_session": "LONDON", "result": "SL",
        "entry_time": "2026-07-15T10:00:00Z",
    }
    values.update(overrides)
    store._conn.execute(
        """INSERT INTO diagnostic_trades (
            id,user_id,ticket_id,direction,trend_status,ema_alignment,rsi_value,
            atr_value,volume_status,market_regime,trading_session,result,entry_time,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (trade_id, user_id, trade_id, values["direction"], values["trend_status"],
         values["ema_alignment"], values["rsi_value"], 2, values["volume_status"],
         values["market_regime"], values["trading_session"], values["result"],
         values["entry_time"], values["entry_time"]),
    )


def test_detects_and_persists_supported_loss_patterns(tmp_path):
    with DiagnosticsStore(tmp_path / "patterns.db") as store:
        _insert_trade(store, "loss_1", "alice", direction="SELL", trend_status="BULLISH",
                      market_regime="RANGING", trading_session="ASIA")
        _insert_trade(store, "loss_2", "alice", ema_alignment="MIXED",
                      market_regime="RANGING", trading_session="ASIA")
        _insert_trade(store, "loss_3", "alice", volume_status="LOW", rsi_value=50)
        _insert_trade(store, "win_1", "alice", result="TP", market_regime="RANGING")
        _insert_trade(store, "other_user", "bob", market_regime="RANGING")
        store._conn.commit()

        patterns = LossPatternDetectionService(store, minimum_support=2).detect(
            "alice", "2026-07-01T00:00:00Z", "2026-07-31T23:59:59Z",
        )
        assert [item["name"] for item in patterns] == [
            "Asia session weakness", "Counter-trend entry", "Ranging market exposure",
        ]
        assert all(item["loss_count"] == 2 for item in patterns)
        assert all(item["loss_percentage"] == 66.67 for item in patterns)
        analysis = store.loss_pattern_analysis("alice")
        assert len(analysis["patterns"]) == 3
        assert analysis["summary"]["totalLosses"] == 3


def test_detection_replaces_same_period_snapshot_idempotently(tmp_path):
    with DiagnosticsStore(tmp_path / "patterns.db") as store:
        _insert_trade(store, "loss_1", "alice", market_regime="RANGING")
        service = LossPatternDetectionService(store, minimum_support=1)
        first = service.detect("alice", "2026-07-01", "2026-07-31T23:59:59Z")
        second = service.detect("alice", "2026-07-01", "2026-07-31T23:59:59Z")
        assert [item["id"] for item in first] == [item["id"] for item in second]
        count = store._conn.execute(
            "SELECT COUNT(*) FROM pola_kekalahan WHERE user_id='alice'"
        ).fetchone()[0]
        assert count == len(second)


def test_detection_validates_inputs(tmp_path):
    with DiagnosticsStore(tmp_path / "patterns.db") as store:
        with pytest.raises(ValueError, match="minimum_support"):
            LossPatternDetectionService(store, minimum_support=0)
        service = LossPatternDetectionService(store)
        with pytest.raises(ValueError, match="user_id"):
            service.detect(" ", "2026-07-01", "2026-07-31")
        with pytest.raises(ValueError, match="period_start"):
            service.detect("alice", "2026-08-01", "2026-07-31")