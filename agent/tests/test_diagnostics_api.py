"""Contract tests for the diagnostics performance summary endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

import api_server


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