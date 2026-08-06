from __future__ import annotations

from types import SimpleNamespace

from src.api.simple_autotrade import (
    DemoAutoTradeRunner,
    StartRequest,
    _ema,
    _fixed_control_pip_size,
    _fixed_controls_levels,
)
from src.trading.auto_trade.strategy_runner import ExecutionMarketData
from src.trading.connectors.mt5._client import MT5Config


def test_ema_is_deterministic():
    values = [float(value) for value in range(1, 30)]
    assert _ema(values, 9) == _ema(values, 9)


def test_cycle_hold_and_duplicate_never_send(monkeypatch):
    from src.trading.connectors.mt5 import _client

    class Fake:
        ACCOUNT_TRADE_MODE_DEMO = 0
        TIMEFRAME_M5 = 5
        def account_info(self): return SimpleNamespace(login=1, trade_mode=0, balance=10_000)
        def symbol_info(self, name): return SimpleNamespace(name=name, trade_allowed=True, point=.01, spread=20, filling_mode=2, trade_tick_size=.01, trade_tick_value=1, volume_min=.01, volume_max=1, volume_step=.01)
        def symbol_info_tick(self, name): return SimpleNamespace(bid=100, ask=100.2, time=1_700_000_000)
        def symbols_get(self): return (self.symbol_info("XAUUSD"),)
        def symbol_select(self, name, enabled=True): return name == "XAUUSD"
        def positions_get(self, **kwargs): return ()
        def orders_get(self, **kwargs): return ()
        def copy_rates_from_pos(self, *args): return [{"time": 1_700_000_000 + i * 300, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0, "tick_volume": 1} for i in range(30)]
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
def test_runner_status_exposes_adaptive_execution_context():
    from src.api.simple_autotrade import RunnerStatus

    status = RunnerStatus(
        running=True,
        state="RUNNING",
        message="adaptive",
        selectedStrategyId="evidence-trend-guard",
        decisionReason="trend confirmed",
        orderType="BUY LIMIT",
        entryPrice=100.0,
        stopLoss=98.0,
        takeProfit=104.0,
    )

    assert status.selectedStrategyId == "evidence-trend-guard"
    assert status.orderType == "BUY LIMIT"
    assert status.takeProfit == 104.0


def test_range_structure_guard_only_blocks_fresh_breaks():
    from types import SimpleNamespace
    from src.trading.auto_trade.strategy_runner import _has_fresh_structure_break

    assert _has_fresh_structure_break(SimpleNamespace(breaks=(SimpleNamespace(index=95),)), 100)
    assert not _has_fresh_structure_break(SimpleNamespace(breaks=(SimpleNamespace(index=80),)), 100)
    assert not _has_fresh_structure_break(SimpleNamespace(breaks=()), 100)


def test_fixed_controls_calculate_levels_from_entry_and_pips():
    pip_size = _fixed_control_pip_size("XAUUSD", 0.01)
    assert pip_size == 0.1
    assert _fixed_controls_levels(True, 100.0, pip_size, 40, 100) == (96.0, 110.0)
    assert _fixed_controls_levels(False, 100.0, pip_size, 40, 100) == (104.0, 90.0)


def test_submit_uses_fixed_controls_and_records_audit_event(monkeypatch):
    class FakeMT5:
        TRADE_ACTION_DEAL = 1
        ORDER_TYPE_BUY = 0
        TRADE_RETCODE_DONE = 10009
        TRADE_RETCODE_DONE_PARTIAL = 10010
        SYMBOL_FILLING_IOC = 2
        ORDER_FILLING_IOC = 1
        ORDER_TIME_GTC = 0

        def order_check(self, payload):
            self.checked = payload
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, comment="ok")

        def order_send(self, payload):
            self.sent = payload
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=12345, deal=0)

    fake = FakeMT5()
    events = []

    def capture_event(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(DemoAutoTradeRunner, "_log_execution", staticmethod(capture_event))
    decision = SimpleNamespace(
        direction="BUY", entry_price=100.0, stop_loss=98.0, take_profit=106.0,
        lot_size=1.97, order_type="MARKET BUY", strategy_id="test-strategy",
    )
    request = StartRequest(lotSize=0.05, stopLossPips=40, takeProfitPips=100)
    market = ExecutionMarketData(
        balance=10_000, tick_size=0.01, tick_value_per_lot=1,
        minimum_lot=0.01, maximum_lot=1, lot_step=0.01, pip_size=0.01,
    )
    runner = DemoAutoTradeRunner()
    runner._submit(
        fake, "XAUUSD", decision, request,
        SimpleNamespace(spread=20, filling_mode=2),
        SimpleNamespace(ask=100.0, bid=99.8), market,
    )

    assert fake.sent["volume"] == 0.05
    assert fake.sent["sl"] == 96.0
    assert fake.sent["tp"] == 110.0
    assert len(events) == 1
    assert events[0]["status"] == "EXECUTED"
    assert events[0]["parameters"].lot_size == 0.05
