"""Contract tests for the diagnostics performance summary endpoint."""

from __future__ import annotations
import sys

import types
from fastapi.testclient import TestClient

import api_server


def test_loss_patterns_returns_empty_analysis(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/patterns"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {
        "totalLosses": 0,
        "classifiedLosses": 0,
        "lossesClassifiedPct": 0.0,
    }
    assert payload["patterns"] == []
    assert payload["insight"]["title"] == "No patterns detected"
    assert payload["generatedAt"]


def test_loss_patterns_returns_latest_user_scoped_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        for index in range(4):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (
                    id,user_id,ticket_id,direction,trend_status,ema_alignment,rsi_value,
                    atr_value,volume_status,market_regime,trading_session,result,
                    entry_time,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"loss_{index}", "alice", f"LOSS-{index}", "SELL", "BEARISH",
                 "BEARISH", 38, 3, "HIGH", "RANGING", "ASIA", "SL",
                 f"2026-07-{index + 1:02d}T10:00:00Z", "2026-07-31T10:00:00Z"),
            )
        pattern_values = (
            "alice", "Counter-trend entry", "TREND", "Against trend", 3, 75.0,
            91.0, "HIGH", '["loss_0","loss_1"]', -5.0,
            "2026-07-01T00:00:00Z", "2026-07-31T23:59:59Z",
            "2026-07-31T23:59:59Z", "now", "now",
        )
        store._conn.execute(
            "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("pattern_latest", *pattern_values),
        )
        store._conn.execute(
            "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("pattern_bob", "bob", *pattern_values[1:]),
        )
        store._conn.commit()

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/patterns?user_id=alice"
    )
    assert response.status_code == 200
    assert response.json() == {
        "summary": {"totalLosses": 4, "classifiedLosses": 3, "lossesClassifiedPct": 75.0},
        "patterns": [{
            "id": "pattern_latest", "name": "Counter-trend entry", "category": "TREND",
            "description": "Against trend", "lossCount": 3, "lossPercentage": 75.0,
            "confidence": 91.0, "severity": "HIGH",
            "evidenceTradeIds": ["loss_0", "loss_1"], "trendDelta": -5.0,
        }],
        "insight": {
            "title": "Primary evidence",
            "detail": "Counter-trend entry is the dominant persisted pattern, accounting for 75% of losses in the latest analysis period.",
        },
        "generatedAt": "2026-07-31T23:59:59Z",
    }


def test_loss_pattern_comparison_calculates_period_deltas(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        base = ("alice", "Counter-trend entry", "TREND", "Against trend")
        metrics = (
            ("current_counter", *base, 4, 40.0, 90.0, "HIGH", "[]", 0.0,
             "2026-07-01", "2026-07-31", "now", "now", "now"),
            ("baseline_counter", *base, 6, 60.0, 90.0, "HIGH", "[]", 0.0,
             "2026-06-01", "2026-06-30", "now", "now", "now"),
            ("current_asia", "alice", "Asia session weakness", "SESSION", "Asia", 2,
             20.0, 80.0, "MEDIUM", "[]", 0.0, "2026-07-01", "2026-07-31",
             "now", "now", "now"),
            ("bob_pattern", "bob", "Bob only", "REGIME", "Hidden", 9, 90.0,
             90.0, "HIGH", "[]", 0.0, "2026-07-01", "2026-07-31",
             "now", "now", "now"),
        )
        store._conn.executemany(
            "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", metrics,
        )
        store._conn.commit()

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/patterns/compare",
        params={
            "user_id": "alice", "current_start": "2026-07-01",
            "current_end": "2026-07-31", "baseline_start": "2026-06-01",
            "baseline_end": "2026-06-30",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"] == {"improving": 1, "worsening": 1, "stable": 0}
    assert [(item["name"], item["deltaPercentagePoints"], item["status"]) for item in payload["patterns"]] == [
        ("Asia session weakness", 20.0, "worsening"),
        ("Counter-trend entry", -20.0, "improving"),
    ]
    assert payload["currentPeriod"] == {"start": "2026-07-01", "end": "2026-07-31"}


def test_loss_pattern_comparison_validates_period_order(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/patterns/compare",
        params={
            "current_start": "2026-08-01", "current_end": "2026-07-31",
            "baseline_start": "2026-06-01", "baseline_end": "2026-06-30",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Period start must not be after period end"


def test_recommendations_returns_empty_user_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/recommendations?user_id=unknown"
    )
    assert response.status_code == 200
    assert response.json()["recommendations"] == []
    assert response.json()["generatedAt"]


def test_recommendations_are_evidence_based_prioritized_and_user_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        rows = (
            ("pattern_trend", "alice", "Counter-trend entry", "TREND", "Trend", 8,
             50.0, 90.0, "HIGH", "[]", 0.0, "2026-07-01", "2026-07-31",
             "2026-07-31T12:00:00Z", "now", "now"),
            ("pattern_session", "alice", "Asia session weakness", "SESSION", "Asia", 3,
             20.0, 70.0, "MEDIUM", "[]", 0.0, "2026-07-01", "2026-07-31",
             "2026-07-31T12:00:00Z", "now", "now"),
            ("pattern_bob", "bob", "Ranging market exposure", "REGIME", "Hidden", 9,
             90.0, 99.0, "HIGH", "[]", 0.0, "2026-07-01", "2026-07-31",
             "2026-07-31T12:00:00Z", "now", "now"),
        )
        store._conn.executemany(
            "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows,
        )
        store._conn.commit()

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/recommendations?user_id=alice"
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["patternId"] for item in payload["recommendations"]] == [
        "pattern_trend", "pattern_session",
    ]
    trend, session = payload["recommendations"]
    assert trend["priority"] == "CRITICAL"
    assert trend["status"] == "READY"
    assert trend["expectedImpact"] == 22.5
    assert trend["evidenceLosses"] == 8
    assert trend["steps"] and trend["validationTarget"] and trend["guardrail"]
    assert session["priority"] == "HIGH"
    assert session["status"] == "REVIEW"
    assert payload["generatedAt"] == "2026-07-31T12:00:00Z"

    critical = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/recommendations?user_id=alice&priority=CRITICAL"
    )
    assert critical.status_code == 200
    assert [item["patternId"] for item in critical.json()["recommendations"]] == [
        "pattern_trend",
    ]

    high = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/recommendations?user_id=alice&priority=HIGH"
    )
    assert high.status_code == 200
    assert [item["patternId"] for item in high.json()["recommendations"]] == [
        "pattern_session",
    ]

    medium = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/recommendations?user_id=alice&priority=MEDIUM"
    )
    assert medium.status_code == 200
    assert medium.json()["recommendations"] == []

    invalid = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/recommendations?user_id=alice&priority=LOW"
    )
    assert invalid.status_code == 422


def test_recommendation_detail_is_complete_and_user_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        store._conn.execute(
            "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("pattern_trend", "alice", "Counter-trend entry", "TREND", "Trend", 8,
             50.0, 90.0, "HIGH", "[]", 0.0, "2026-07-01", "2026-07-31",
             "2026-07-31T12:00:00Z", "now", "now"),
        )
        store._conn.commit()

    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    response = client.get(
        "/diagnostics/recommendations/rec_pattern_trend?user_id=alice"
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "rec_pattern_trend",
        "title": "Require aligned trend confirmation",
        "summary": (
            "Counter-trend entry accounts for 50% of losses in the latest "
            "persisted analysis period."
        ),
        "action": (
            "Require the higher-timeframe trend and EMA alignment to agree before "
            "opening a position."
        ),
        "patternId": "pattern_trend",
        "patternName": "Counter-trend entry",
        "priority": "CRITICAL",
        "status": "READY",
        "expectedImpact": 22.5,
        "evidenceLosses": 8,
        "confidence": 90.0,
        "effort": "MEDIUM",
        "steps": [
            "Read the higher-timeframe trend before evaluating an entry signal.",
            "Require trend direction and EMA alignment to agree with the proposed side.",
            "Reject the entry when either confirmation is mixed or opposite.",
        ],
        "validationTarget": (
            "Reduce counter-trend loss share below 30% over the next 100 trades."
        ),
        "guardrail": (
            "Do not relax the existing spread, exposure, or stop-loss controls."
        ),
    }
    assert client.get(
        "/diagnostics/recommendations/rec_pattern_trend?user_id=bob"
    ).status_code == 404
    missing = client.get(
        "/diagnostics/recommendations/rec_unknown?user_id=alice"
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Diagnostic recommendation not found"


def test_improvement_timeline_is_ordered_limited_and_user_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    rows = (
        ("imp_old", "alice", "rec_old", "Old control", "Earlier change", "APPLIED",
         45.0, 35.0, None, None, None, "2026-07-20T10:00:00Z", "Team A", None,
         "2026-07-20T09:00:00Z", "2026-07-20T10:00:00Z"),
        ("imp_new", "alice", "rec_new", "New control", "Latest change", "MONITORING",
         45.0, 30.0, 38.0, "2026-07-21", "2026-08-21", None, "Team B",
         "Collecting evidence", "2026-07-21T09:00:00Z", "2026-07-31T10:00:00Z"),
        ("imp_bob", "bob", "rec_bob", "Hidden control", "Other user", "VALIDATED",
         50.0, 30.0, 25.0, None, None, "2026-08-01T10:00:00Z", "Bob", None,
         "2026-08-01T09:00:00Z", "2026-08-01T10:00:00Z"),
    )
    with DiagnosticsStore(db_path) as store:
        store._conn.executemany(
            "INSERT INTO improvement_logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows,
        )
        store._conn.commit()

    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    response = client.get(
        "/diagnostics/improvements/timeline?user_id=alice&limit=1"
    )
    assert response.status_code == 200
    assert response.json() == [{
        "id": "imp_new",
        "recommendationId": "rec_new",
        "title": "New control",
        "description": "Latest change",
        "status": "MONITORING",
        "occurredAt": "2026-07-31T10:00:00Z",
        "owner": "Team B",
        "evidenceNote": "Collecting evidence",
    }]
    assert client.get(
        "/diagnostics/improvements/timeline?user_id=unknown"
    ).json() == []
    assert client.get(
        "/diagnostics/improvements/timeline?limit=201"
    ).status_code == 422


def test_improvement_loss_reduction_returns_measured_user_scoped_points(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        for index, result in enumerate(("TP", "SL", "TP")):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (
                    id,user_id,ticket_id,direction,trend_status,ema_alignment,rsi_value,
                    atr_value,volume_status,market_regime,trading_session,result,
                    entry_time,created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"chart_{index}", "alice", f"CHART-{index}", "BUY", "BULLISH",
                 "BULLISH", 60, 3, "NORMAL", "TRENDING", "LONDON", result,
                 f"2026-07-{index + 1:02d}T10:00:00Z", "now"),
            )
        rows = (
            ("imp_1", "alice", "rec_1", "First", "First", "VALIDATED", 45.2,
             35.0, 40.0, "2026-07-01", "2026-07-03T23:59:59Z", "2026-07-01",
             "Team", None, "now", "2026-07-03"),
            ("imp_2", "alice", "rec_2", "Second", "Second", "MONITORING", 40.0,
             30.0, 37.1, "2026-07-01", "2026-07-03T23:59:59Z", "2026-07-10",
             "Team", None, "now", "2026-07-10"),
            ("imp_bob", "bob", "rec_bob", "Hidden", "Hidden", "VALIDATED", 90.0,
             20.0, 10.0, None, None, "2026-07-01", "Bob", None, "now", "now"),
        )
        store._conn.executemany(
            "INSERT INTO improvement_logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows,
        )
        store._conn.commit()

    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    response = client.get("/diagnostics/improvements/loss-reduction?user_id=alice")
    assert response.status_code == 200
    assert response.json() == [
        {"label": "Baseline", "lossRate": 45.2, "tradeCount": 0},
        {"label": "Change 1", "lossRate": 40.0, "tradeCount": 3},
        {"label": "Change 2", "lossRate": 37.1, "tradeCount": 3},
    ]
    assert client.get(
        "/diagnostics/improvements/loss-reduction?user_id=unknown"
    ).json() == []


def test_improvement_success_metrics_calculates_progress_and_status(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        rows = (
            ("imp_done", "alice", "rec_done", "Trend gate", "Trend", "VALIDATED", 45.0, 30.0, 27.0, None, None, "2026-07-31", "Team", None, "now", "2026-07-31"),
            ("imp_track", "alice", "rec_track", "Regime gate", "Regime", "MONITORING", 45.0, 30.0, 37.5, None, None, "2026-07-30", "Team", None, "now", "2026-07-30"),
            ("imp_risk", "alice", "rec_risk", "Asia risk", "Risk", "MONITORING", 45.0, 30.0, None, None, None, None, "Team", None, "now", "2026-07-29"),
        )
        store._conn.executemany(
            "INSERT INTO improvement_logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows,
        )
        store._conn.commit()

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/improvements/success-metrics?user_id=alice"
    )
    assert response.status_code == 200
    payload = response.json()
    assert [(item["id"], item["status"], item["progress"]) for item in payload] == [
        ("metric_imp_done", "ACHIEVED", 100.0),
        ("metric_imp_track", "ON_TRACK", 50.0),
        ("metric_imp_risk", "AT_RISK", 0.0),
    ]


def test_improvement_activity_returns_typed_latest_user_events(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        rows = (
            ("imp_evidence", "alice", "rec_evidence", "Trend gate", "Trend", "VALIDATED", 45.0, 30.0, 27.0, None, None, None, "Engine", None, "now", "2026-07-31"),
            ("imp_note", "alice", "rec_note", "Regime gate", "Regime", "MONITORING", 45.0, 30.0, None, None, None, None, "Team", "Replay looks stable", "now", "2026-07-30"),
            ("imp_status", "alice", "rec_status", "Asia risk", "Risk", "APPLIED", 45.0, 30.0, None, None, None, None, "Trader", None, "now", "2026-07-29"),
            ("imp_bob", "bob", "rec_bob", "Hidden", "Hidden", "VALIDATED", 50.0, 20.0, 10.0, None, None, None, "Bob", None, "now", "2026-08-01"),
        )
        store._conn.executemany(
            "INSERT INTO improvement_logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows,
        )
        store._conn.commit()

    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    response = client.get("/diagnostics/improvements/activity?user_id=alice")
    assert response.status_code == 200
    payload = response.json()
    assert [item["type"] for item in payload] == ["EVIDENCE", "NOTE", "STATUS_CHANGE"]
    assert payload[0]["message"] == "Recorded 27% current loss rate for Trend gate."
    assert payload[1]["message"] == "Replay looks stable"
    assert payload[2]["actor"] == "Trader"
    assert client.get(
        "/diagnostics/improvements/activity?user_id=bob&limit=1"
    ).json()[0]["recommendationId"] == "rec_bob"


def test_improvement_report_pdf_exports_selected_sections_and_escapes_html(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        store._conn.execute(
            "INSERT INTO improvement_logs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("imp_pdf", "alice", "rec_pdf", "<Trend gate>", "Change & verify", "VALIDATED", 45.0, 30.0, 28.0, None, None, "2026-07-31", "Owner", "<safe>", "now", "2026-07-31"),
        )
        store._conn.commit()

    captured: dict[str, str] = {}
    class FakeHTML:
        def __init__(self, *, string: str):
            captured["html"] = string

        def write_pdf(self):
            return b"%PDF-fake"

    monkeypatch.setitem(sys.modules, "weasyprint", types.SimpleNamespace(HTML=FakeHTML))
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).post(
        "/diagnostics/improvements/export/pdf",
        json={"user_id": "alice", "sections": ["metrics"]},
    )
    assert response.status_code == 200
    assert response.content == b"%PDF-fake"
    assert response.headers["content-type"] == "application/pdf"
    assert "improvement-progress.pdf" in response.headers["content-disposition"]
    assert "&lt;Trend gate&gt;" in captured["html"]
    assert "Activity log" not in captured["html"]


def test_improvement_report_pdf_rejects_empty_sections(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).post(
        "/diagnostics/improvements/export/pdf",
        json={"user_id": "alice", "sections": []},
    )
    assert response.status_code == 422


def test_recommendation_status_can_be_applied_persisted_and_reopened(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        store._conn.execute(
            "INSERT INTO pola_kekalahan VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("pattern_trend", "alice", "Counter-trend entry", "TREND", "Trend", 8,
             50.0, 90.0, "HIGH", "[]", 0.0, "2026-07-01", "2026-07-31",
             "2026-07-31T12:00:00Z", "now", "now"),
        )
        store._conn.commit()

    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    endpoint = "/diagnostics/recommendations/rec_pattern_trend/status"
    applied = client.patch(endpoint, json={"user_id": "alice", "status": "APPLIED"})
    assert applied.status_code == 200
    assert applied.json()["status"] == "APPLIED"
    assert client.get(
        "/diagnostics/recommendations/rec_pattern_trend?user_id=alice"
    ).json()["status"] == "APPLIED"
    assert client.get(
        "/diagnostics/recommendations?user_id=alice"
    ).json()["recommendations"][0]["status"] == "APPLIED"

    reopened = client.patch(endpoint, json={"user_id": "alice", "status": "READY"})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "READY"
    assert client.patch(
        endpoint, json={"user_id": "bob", "status": "APPLIED"},
    ).status_code == 404


def test_recommendation_status_rejects_invalid_request(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    endpoint = "/diagnostics/recommendations/rec_unknown/status"
    assert client.patch(endpoint, json={"user_id": "alice", "status": "DONE"}).status_code == 422
    missing = client.patch(endpoint, json={"user_id": "alice", "status": "APPLIED"})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Diagnostic recommendation not found"


def test_diagnostics_summary_returns_empty_user_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))

    response = client.get("/diagnostics/summary")

    assert response.status_code == 200
    assert response.json() == {
        "totalTrades": 0,
        "winningTrades": 0,
        "losingTrades": 0,
        "lossRate": 0.0,
    }


def test_diagnostics_summary_aggregates_trade_results(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        for ticket, result in (("t1", "TP"), ("t2", "TP"), ("t3", "SL")):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (
                    id, user_id, ticket_id, direction, trend_status, ema_alignment,
                    rsi_value, atr_value, volume_status, market_regime,
                    trading_session, result, entry_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ticket, "alice", ticket, "BUY", "BULLISH", "BULLISH", 60, 2, "NORMAL", "TRENDING", "LONDON", result, "2026-07-30T10:00:00Z", "2026-07-30T10:00:00Z"),
            )
        store._conn.commit()

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/summary?user_id=alice"
    )
    assert response.status_code == 200
    assert response.json() == {
        "totalTrades": 3,
        "winningTrades": 2,
        "losingTrades": 1,
        "lossRate": 33.33,
    }


def test_diagnostic_causes_are_ranked_against_all_losses(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        reasons = ("Counter-trend entry", "Market ranging", "Counter-trend entry", None)
        for index, reason in enumerate(reasons):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (
                    id, user_id, ticket_id, direction, trend_status, ema_alignment,
                    rsi_value, atr_value, volume_status, market_regime,
                    trading_session, result, suspected_reason, entry_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"loss_{index}", "alice", f"loss_{index}", "SELL", "BEARISH", "BEARISH", 38, 3, "HIGH", "RANGING", "ASIA", "SL", reason, "2026-07-30T10:00:00Z", "2026-07-30T10:00:00Z"),
            )
        store._conn.commit()

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/causes?user_id=alice"
    )
    assert response.status_code == 200
    assert response.json() == [
        {"label": "Counter-trend entry", "count": 2, "percentage": 50.0},
        {"label": "Market ranging", "count": 1, "percentage": 25.0},
    ]


def test_recent_trades_are_limited_ordered_and_user_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        for index, (user, entry_time) in enumerate((("alice", "2026-07-30T10:00:00Z"), ("alice", "2026-07-30T11:00:00Z"), ("bob", "2026-07-30T12:00:00Z"))):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (
                    id, user_id, ticket_id, direction, trend_status, ema_alignment,
                    rsi_value, atr_value, volume_status, market_regime,
                    trading_session, result, entry_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"trade_{index}", user, f"ticket_{index}", "BUY", "BULLISH", "BULLISH", 60, 2, "NORMAL", "TRENDING", "LONDON", "TP", entry_time, entry_time),
            )
        store._conn.commit()

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/trades/recent?user_id=alice&limit=1"
    )
    assert response.status_code == 200
    assert response.json()[0]["ticketId"] == "ticket_1"


def test_diagnostics_insight_uses_dominant_cause(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore

    with DiagnosticsStore(db_path) as store:
        for index, reason in enumerate(("Counter-trend entry", "Counter-trend entry", "Asia session")):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (
                    id, user_id, ticket_id, direction, trend_status, ema_alignment,
                    rsi_value, atr_value, volume_status, market_regime,
                    trading_session, result, suspected_reason, entry_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"insight_{index}", "alice", f"insight_{index}", "BUY", "BULLISH", "MIXED", 55, 2, "NORMAL", "RANGING", "ASIA", "SL", reason, "2026-07-30T10:00:00Z", "2026-07-30T10:00:00Z"),
            )
        store._conn.commit()

    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/insight?user_id=alice"
    )
    assert response.status_code == 200
    assert response.json()["cause"] == "Counter-trend entry"
    assert response.json()["percentage"] == 66.67


def test_diagnostics_insight_is_empty_without_diagnosed_losses(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get("/diagnostics/insight")
    assert response.status_code == 200
    assert response.json() is None


def test_trade_list_supports_search_result_and_pagination(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore
    with DiagnosticsStore(db_path) as store:
        for index, (user, ticket, result) in enumerate((("alice", "GOLD-1", "SL"), ("alice", "GOLD-2", "TP"), ("bob", "GOLD-3", "SL"))):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (id,user_id,ticket_id,direction,trend_status,ema_alignment,rsi_value,atr_value,volume_status,market_regime,trading_session,result,suspected_reason,entry_time,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"list_{index}",user,ticket,"BUY","BULLISH","MIXED",60,2,"NORMAL","RANGING","ASIA",result,"Counter-trend entry",f"2026-07-3{index}T10:00:00Z",f"2026-07-3{index}T10:00:00Z"),
            )
        store._conn.commit()
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/trades?user_id=alice&search=GOLD&result=SL&limit=1"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["ticket_id"] == "GOLD-1"


def test_trade_detail_is_user_scoped_and_returns_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore
    with DiagnosticsStore(db_path) as store:
        store._conn.execute(
            """INSERT INTO diagnostic_trades (id,user_id,ticket_id,direction,trend_status,ema_alignment,rsi_value,atr_value,volume_status,market_regime,trading_session,result,suspected_reason,profit_loss,entry_time,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("detail_1", "alice", "XAU-DETAIL", "BUY", "BEARISH", "MIXED", 61, 3.4, "NORMAL", "RANGING", "ASIA", "SL", "Counter-trend entry", -82.4, "2026-07-30T10:00:00Z", "2026-07-30T10:00:00Z"),
        )
        store._conn.commit()
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    response = client.get("/diagnostics/trades/detail_1?user_id=alice")
    assert response.status_code == 200
    assert response.json()["ticket_id"] == "XAU-DETAIL"
    assert response.json()["rsi_value"] == 61
    assert client.get("/diagnostics/trades/detail_1?user_id=bob").status_code == 404


def test_selected_trade_csv_export_is_downloadable_and_user_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore
    with DiagnosticsStore(db_path) as store:
        store._conn.execute(
            """INSERT INTO diagnostic_trades (id,user_id,ticket_id,direction,trend_status,ema_alignment,rsi_value,atr_value,volume_status,market_regime,trading_session,result,entry_time,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("export_1", "alice", "CSV-TICKET", "SELL", "BEARISH", "BEARISH", 38, 4, "HIGH", "TRENDING", "LONDON", "TP", "2026-07-30T10:00:00Z", "2026-07-30T10:00:00Z"),
        )
        store._conn.commit()
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).post(
        "/diagnostics/trades/export",
        json={"trade_ids": ["export_1"], "format": "csv", "user_id": "alice"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "CSV-TICKET" in response.text


def test_trade_list_supports_market_and_indicator_filters(tmp_path, monkeypatch):
    db_path = tmp_path / "diagnostics.db"
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(db_path))
    from src.diagnostics.store import DiagnosticsStore
    with DiagnosticsStore(db_path) as store:
        for index, (regime, session, rsi) in enumerate((("RANGING", "ASIA", 61), ("TRENDING", "LONDON", 38))):
            store._conn.execute(
                """INSERT INTO diagnostic_trades (id,user_id,ticket_id,direction,trend_status,ema_alignment,rsi_value,atr_value,volume_status,market_regime,trading_session,result,entry_time,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"filter_{index}","alice",f"FILTER-{index}","BUY","BULLISH","MIXED",rsi,3,"NORMAL",regime,session,"SL","2026-07-30T10:00:00Z","2026-07-30T10:00:00Z"),
            )
        store._conn.commit()
    response = TestClient(api_server.app, client=("127.0.0.1", 50000)).get(
        "/diagnostics/trades?user_id=alice&market_regime=RANGING&trading_session=ASIA&min_rsi=60"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["ticket_id"] == "FILTER-0"
    assert response.json()["items"][0]["rsi_value"] == 61
    assert response.json()["items"][0]["ema_alignment"] == "MIXED"


def test_save_custom_filter_creates_then_updates_named_preset(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    first = client.post("/diagnostics/filters", json={"user_id":"alice","name":"Asia losses","criteria":{"session":"ASIA"}})
    second = client.post("/diagnostics/filters", json={"user_id":"alice","name":"Asia losses","criteria":{"session":"ASIA","result":"SL"}})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["criteria"] == {"session":"ASIA","result":"SL"}


def test_list_custom_filters_is_user_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    client.post("/diagnostics/filters", json={"user_id":"alice","name":"Alice filter","criteria":{"result":"SL"}})
    client.post("/diagnostics/filters", json={"user_id":"bob","name":"Bob filter","criteria":{"result":"TP"}})
    response = client.get("/diagnostics/filters?user_id=alice")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Alice filter"]


def test_delete_custom_filter_is_user_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("VIBE_TRADING_DIAGNOSTICS_DB_PATH", str(tmp_path / "diagnostics.db"))
    client = TestClient(api_server.app, client=("127.0.0.1", 50000))
    created = client.post("/diagnostics/filters", json={"user_id":"alice","name":"Delete me","criteria":{"result":"SL"}}).json()
    assert client.delete(f"/diagnostics/filters/{created['id']}?user_id=bob").status_code == 404
    deleted = client.delete(f"/diagnostics/filters/{created['id']}?user_id=alice")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}
    assert client.get("/diagnostics/filters?user_id=alice").json() == []