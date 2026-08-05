from __future__ import annotations

from types import SimpleNamespace

from src.api.simple_autotrade import DemoAutoTradeRunner, StartRequest, _ema
from src.trading.connectors.mt5._client import MT5Config


def test_ema_is_deterministic():
    values = [float(value) for value in range(1, 30)]
    assert _ema(values, 9) == _ema(values, 9)


def test_cycle_hold_and_duplicate_never_send(monkeypatch):
    from src.trading.connectors.mt5 import _client

    class Fake:
        ACCOUNT_TRADE_MODE_DEMO = 0
        TIMEFRAME_M5 = 5
        def account_info(self): return SimpleNamespace(login=1, trade_mode=0)
        def symbol_info(self, name): return SimpleNamespace(name=name, trade_allowed=True, point=.01, spread=20, filling_mode=2)
        def symbol_info_tick(self, name): return SimpleNamespace(bid=100, ask=100.2, time=1_700_000_000)
        def symbols_get(self): return (self.symbol_info("XAUUSD"),)
        def symbol_select(self, name, enabled=True): return name == "XAUUSD"
        def positions_get(self, **kwargs): return ()
        def copy_rates_from_pos(self, *args): return [{"time": 1_700_000_000 + i * 300, "close": 100.0} for i in range(30)]
        def order_check(self, payload): raise AssertionError("HOLD must not check")
        def order_send(self, payload): raise AssertionError("HOLD must not send")
        def initialize(self, *args, **kwargs): return True
        def shutdown(self): pass

    fake = Fake()
    monkeypatch.setattr(_client, "_require_mt5", lambda: fake)
    monkeypatch.setattr(_client, "load_config", lambda: MT5Config(login=1, password="x", server="demo", profile="paper"))
    runner = DemoAutoTradeRunner()
    request = StartRequest()
    runner._cycle(_client.load_config(), request)
    first = runner.status()
    runner._cycle(_client.load_config(), request)
    assert first.lastDecision == "HOLD"
    assert runner.status().lastCandleAt == first.lastCandleAt


def test_preflight_rejects_real_account(monkeypatch):
    from src.trading.connectors.mt5 import _client

    class Fake:
        ACCOUNT_TRADE_MODE_DEMO = 0
        def initialize(self, *args, **kwargs): return True
        def shutdown(self): pass
        def account_info(self): return SimpleNamespace(login=1, trade_mode=2)

    monkeypatch.setattr(_client, "_require_mt5", lambda: Fake())
    runner = DemoAutoTradeRunner()
    config = MT5Config(login=1, password="x", server="real", profile="paper")
    try:
        runner._preflight(config, StartRequest())
    except Exception as exc:
        assert "DEMO" in str(exc) or "paper" in str(exc)
    else:
        raise AssertionError("real account must be rejected")