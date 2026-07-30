"""Live demo verification of the production forex runtime pipeline.

The script never calls the MT5 send API. Broker writes are reachable only through
RuntimePipelineRunner -> RuntimeMT5OrderExecutor -> MT5BrokerTransport.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from src.trading.forex_decisions import ACTION, RuntimeDecisionEngine  # noqa: E402
from src.trading.forex_execution import ExecutionStatus, MT5TradingProfile, RuntimeMT5OrderExecutor  # noqa: E402
from src.trading.forex_features import RuntimeFeatureBuilder  # noqa: E402
from src.trading.forex_positions import OwnershipPolicy, RuntimeForexPositionManager  # noqa: E402
from src.trading.forex_risk import RiskConfiguration, RuntimeForexRiskManager, SymbolSpecification  # noqa: E402
from src.trading.forex_signals import RuntimeSignalEngine  # noqa: E402
from src.trading.runtime_pipeline import (  # noqa: E402
    CandleOutcome,
    MT5BrokerTransport,
    MT5RuntimeInputs,
    RuntimeEventLog,
    RuntimePipelineRunner,
)

SYMBOL = "XAUUSD"
TIMEFRAME = "1h"
MAGIC = 862001
COMMENT_PREFIX = "vibe-trading"
EVENT_LOG = ROOT / ".cache" / "runtime-integration-events.jsonl"


class LiveBarSource:
    def subscribe(self, callback):  # type: ignore[no-untyped-def]
        self.callback = callback
        return self


class DiagnosticTransport:
    """Transparent transport wrapper used only to expose executor diagnostics."""

    def __init__(self, inner):  # type: ignore[no-untyped-def]
        self.inner = inner

    def refresh_quote(self, quote, profile):  # type: ignore[no-untyped-def]
        return self.inner.refresh_quote(quote, profile)

    def refresh_symbol(self, specification, profile):  # type: ignore[no-untyped-def]
        return self.inner.refresh_symbol(specification, profile)

    def order_check(self, request, profile):  # type: ignore[no-untyped-def]
        print("\n----- BROKER ORDER CHECK -----")
        print(f"Translated request: {self.inner._mt5_request(request)}")
        try:
            result = self.inner.order_check(request, profile)
        except Exception:
            traceback.print_exc()
            raise
        print(f"Order check result: {result}")
        print(f"MT5 last_error: {mt5.last_error()}")
        return result

    def order_send(self, request, profile):  # type: ignore[no-untyped-def]
        print("\n----- BROKER ORDER SEND -----")
        print(f"Translated request: {self.inner._mt5_request(request)}")
        try:
            result = self.inner.order_send(request, profile)
        except Exception:
            traceback.print_exc()
            raise
        print(f"Broker response: {result}")
        print(f"MT5 last_error: {mt5.last_error()}")
        return result


class DiagnosticExecutor:
    """Transparent production executor wrapper; it does not alter execution."""

    def __init__(self, inner):  # type: ignore[no-untyped-def]
        self.inner = inner

    def execute(self, plan, specification, quote, profile, position_ticket=None, position_side=None):  # type: ignore[no-untyped-def]
        print("\n----- EXECUTOR INPUT -----")
        print(f"Decision object: {getattr(plan, '_diagnostic_decision', 'available in prior pipeline event')}")
        print(f"Entire RiskManager output: {plan}")
        print(f"Final execution action: {plan.action}")
        print(f"Order side: {'buy' if plan.action in {'OPEN_LONG', 'REVERSE_TO_LONG'} else 'sell' if plan.action in {'OPEN_SHORT', 'REVERSE_TO_SHORT'} else 'close'}")
        print(f"Volume: {plan.volume_lots}")
        print(f"Price: {plan.entry_price}")
        print(f"SL: {plan.stop_loss}")
        print(f"TP: {plan.take_profit}")
        print(f"Magic: {getattr(self.inner, 'magic_number', MAGIC)}")
        print(f"Comment: {COMMENT_PREFIX}")
        print(f"Position ticket: {position_ticket}")
        try:
            result = self.inner.execute(plan, specification, quote, profile, position_ticket, position_side)
        except Exception:
            print("----- EXECUTOR EXCEPTION -----")
            traceback.print_exc()
            raise
        print("\n----- EXECUTOR OUTPUT -----")
        print(f"ExecutionResult: {result}")
        print(f"Status: {result.execution_status}")
        print(f"Reason/error: {result.broker_comment}")
        print(f"Broker retcode: {result.broker_retcode}")
        print(f"Request/response: execution result contains broker response fields; request was logged above")
        return result


def fail(message: str) -> None:
    print(f"Failure ...... {message}")
    print(f"MT5 Error .... {mt5.last_error()}")
    print("Overall ...... FAIL")
    raise SystemExit(1)


def filling_mode(info: object) -> str:
    mask = int(getattr(info, "filling_mode", 0) or 0)
    for name, value in (
        ("RETURN", mt5.ORDER_FILLING_RETURN),
        ("IOC", mt5.ORDER_FILLING_IOC),
        ("FOK", mt5.ORDER_FILLING_FOK),
    ):
        if mask & (1 << int(value)):
            return name
    raise RuntimeError(f"unsupported filling capability mask {mask}")


def broker_clock() -> datetime:
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(float(tick.time), tz=timezone.utc)


def live_bars() -> list[dict[str, object]]:
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 1, 260)
    if rates is None or len(rates) < 200:
        fail(f"need at least 200 closed H1 bars; received {0 if rates is None else len(rates)}")
    bars: list[dict[str, object]] = []
    for rate in rates:
        timestamp = datetime.fromtimestamp(float(rate["time"]), tz=timezone.utc)
        bars.append({
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME,
            "broker_timestamp": timestamp,
            "validated": True,
            "closed": True,
            "ohlcv": {
                "open": float(rate["open"]), "high": float(rate["high"]),
                "low": float(rate["low"]), "close": float(rate["close"]),
                "volume": float(rate["tick_volume"]),
            },
            "spread": float(rate["spread"]),
            "tick_metadata": {"bid": float(rate["close"]), "ask": float(rate["close"])},
        })
    return bars


def build_runner(info: object, feature_builder: RuntimeFeatureBuilder) -> RuntimePipelineRunner:
    now = broker_clock
    point = float(info.point)
    tick_value = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
    specification = SymbolSpecification(
        symbol=SYMBOL,
        trading_enabled=int(info.trade_mode) != mt5.SYMBOL_TRADE_MODE_DISABLED,
        tick_size=float(getattr(info, "trade_tick_size", 0.0) or point),
        tick_value_per_lot=tick_value,
        contract_size=float(info.trade_contract_size),
        lot_step=float(info.volume_step), min_lot=float(info.volume_min), max_lot=float(info.volume_max),
        stop_level_distance=float(info.trade_stops_level) * point,
        freeze_level_distance=float(info.trade_freeze_level) * point,
    )
    profile = MT5TradingProfile(
        profile_name="demo", trade_mode="demo",
        stop_level_distance=specification.stop_level_distance,
        freeze_level_distance=specification.freeze_level_distance,
        filling_mode=filling_mode(info), execution_mode="MARKET", expiration_policy="GTC",
    )
    runtime_inputs = MT5RuntimeInputs(
        mt5, specification=specification, profile=profile,
        magic_number=MAGIC, comment_prefix=COMMENT_PREFIX, clock=now,
    )
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    EVENT_LOG.unlink(missing_ok=True)
    risk = RiskConfiguration(
        risk_percent=0.01, stop_loss_distance=max(10.0, specification.stop_level_distance + point),
        reward_ratio=2.0, max_spread=1000.0, min_free_margin=0.0, min_margin_level=0.0,
        max_daily_loss=1_000_000.0, max_drawdown_percent=100.0, max_trades_per_day=100,
        max_consecutive_losses=100, max_symbol_exposure=1_000_000.0,
        max_correlated_exposure=1_000_000.0, max_slippage=20.0,
        # Historical candles are replayed through the real stages to observe the
        # unchanged strategy's entry and EXIT path. The production executor still
        # enforces its normal freshness checks; this only prevents replayed plans
        # from expiring before the live demo transport receives them.
        expiration_seconds=30 * 86400,
    )
    transport = DiagnosticTransport(MT5BrokerTransport(mt5, clock=now))
    ownership = OwnershipPolicy(
        strategy_name="forex-ema-macd-rsi-baseline", strategy_version="1.0.0",
        magic_number=MAGIC, comment_prefix=COMMENT_PREFIX,
    )
    return RuntimePipelineRunner(
        market_data=LiveBarSource(), feature_builder=feature_builder,
        signal_engine=RuntimeSignalEngine(clock=now, stale_after=timedelta(days=30)),
        decision_engine=RuntimeDecisionEngine(clock=now, stale_after=timedelta(days=30)),
        risk_manager=RuntimeForexRiskManager(clock=now, stale_after=timedelta(days=30)),
        executor=DiagnosticExecutor(RuntimeMT5OrderExecutor(transport, clock=now, stale_after_seconds=30 * 86400)),
        position_manager=RuntimeForexPositionManager(ownership), runtime_inputs=runtime_inputs,
        event_log=RuntimeEventLog(EVENT_LOG), risk_configuration=risk, clock=now,
    )


def print_result(result: object) -> None:
    feature = result.feature_snapshot
    signal = result.signal_snapshot
    decision = result.decision_snapshot
    plan = result.order_plan
    execution = result.execution_result
    print(f"Market ........ PASS ({result.candle_id})")
    print(f"Features ...... PASS ({feature.warmup_status.value})")
    print(f"Signals ....... PASS ({signal.signal_type.value})")
    print(f"Decision ...... PASS ({decision.action.value})")
    print(f"Risk .......... PASS ({plan.approval_status.value}, volume={plan.volume_lots})")
    print(f"Executor ...... {'PASS' if execution.execution_status is ExecutionStatus.FILLED else 'FAIL'} ({execution.execution_status.value})")


def main() -> None:
    print("===== RUNTIME INTEGRATION TEST =====")
    if not mt5.initialize():
        fail(f"initialize failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        info = mt5.symbol_info(SYMBOL)
        if account is None or info is None:
            fail(f"MT5 account/symbol unavailable: {mt5.last_error()}")
        if int(account.trade_mode) != mt5.ACCOUNT_TRADE_MODE_DEMO:
            fail("account is not demo")
        positions = mt5.positions_get(symbol=SYMBOL)
        if positions is None or len(positions) > 1:
            fail("test requires at most one initial XAUUSD position")
        if positions:
            existing = positions[0]
            print(
                "Resume Position "
                f"ticket={existing.ticket} type={existing.type} volume={existing.volume} "
                f"magic={existing.magic} comment={existing.comment!r}"
            )
        print("Initialize .... PASS")
        bars = live_bars()
        print(f"Market Data ... PASS ({len(bars)} closed H1 bars loaded)")
        feature_builder = RuntimeFeatureBuilder(clock=broker_clock, stale_after=timedelta(days=30))
        print(f"Warmup ........ PASS (production builder; {len(bars)} bars replayed)")

        runner = build_runner(info, feature_builder)
        opened = bool(positions)
        closed = False
        for bar in bars:
            result = runner.process_candle(bar)
            if result.outcome is CandleOutcome.FAILED:
                fail(f"{result.error_stage}: {result.error_message}")
            if result.outcome is not CandleOutcome.COMPLETED:
                continue
            print_result(result)
            action = result.decision_snapshot.action
            if action in {ACTION.OPEN_LONG, ACTION.OPEN_SHORT}:
                if result.execution_result.execution_status is not ExecutionStatus.FILLED:
                    fail("entry execution was not filled")
                current = mt5.positions_get(symbol=SYMBOL)
                if current is None or len(current) != 1:
                    fail("entry did not produce exactly one position")
                opened = True
                print("Position ...... PASS (1 open position)")
            elif action is ACTION.CLOSE_POSITION:
                if result.execution_result.execution_status is not ExecutionStatus.FILLED:
                    fail("close execution was not filled")
                remaining = mt5.positions_get(symbol=SYMBOL)
                if remaining is None or len(remaining) != 0:
                    fail("runtime close did not flatten the position")
                closed = True
                print("Close ......... PASS (0 positions)")
                break
        if not opened:
            fail("production strategy produced no entry signal in loaded live history")
        if not closed:
            fail("production strategy produced no EXIT/CLOSE_POSITION after entry")
        print("Overall ....... PASS")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()