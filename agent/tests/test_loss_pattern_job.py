"""Tests for the periodic loss-pattern refresh job."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from src.diagnostics.pattern_job import (
    _interval_seconds,
    _month_period,
    run_pattern_refresh_once,
)
from src.diagnostics.store import DiagnosticsStore


def _insert_loss(store: DiagnosticsStore, trade_id: str, user_id: str) -> None:
    store._conn.execute(
        """INSERT INTO diagnostic_trades (
            id,user_id,ticket_id,direction,trend_status,ema_alignment,rsi_value,
            atr_value,volume_status,market_regime,trading_session,result,entry_time,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (trade_id, user_id, trade_id, "SELL", "BULLISH", "MIXED", 50, 2,
         "LOW", "RANGING", "ASIA", "SL", "2026-07-15T10:00:00+00:00",
         "2026-07-15T10:00:00+00:00"),
    )


def test_month_period_uses_stable_utc_boundaries():
    start, end = _month_period(datetime(2026, 12, 20, tzinfo=timezone.utc))
    assert start == "2026-12-01T00:00:00+00:00"
    assert end == "2026-12-31T23:59:59.999999+00:00"


def test_refresh_job_updates_each_active_loss_user(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    with DiagnosticsStore(db_path) as store:
        _insert_loss(store, "alice_1", "alice")
        _insert_loss(store, "alice_2", "alice")
        _insert_loss(store, "bob_1", "bob")
        _insert_loss(store, "bob_2", "bob")
        store._conn.commit()

    result = run_pattern_refresh_once(now=datetime(2026, 7, 20, tzinfo=timezone.utc))
    assert result == {"refreshed": 2, "failed": 0}
    with DiagnosticsStore(db_path) as store:
        assert store._conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM pola_kekalahan"
        ).fetchone()[0] == 2


def test_interval_has_safe_minimum_and_fallback(monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_PATTERN_JOB_INTERVAL_SECONDS", "1")
    assert _interval_seconds() == 60
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_PATTERN_JOB_INTERVAL_SECONDS", "invalid")
    assert _interval_seconds() == 21600


def test_start_and_stop_are_idempotent(monkeypatch):
    import src.diagnostics.pattern_job as job

    calls = 0

    def fake_run() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"refreshed": 0, "failed": 0}

    monkeypatch.setattr(job, "run_pattern_refresh_once", fake_run)
    monkeypatch.setattr(job, "_interval_seconds", lambda: 60)
    async def exercise_lifecycle() -> None:
        job.start_pattern_refresh_job()
        job.start_pattern_refresh_job()
        await job.stop_pattern_refresh_job()
        await job.stop_pattern_refresh_job()

    asyncio.run(exercise_lifecycle())
    assert calls <= 1