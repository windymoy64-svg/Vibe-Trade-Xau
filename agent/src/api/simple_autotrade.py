"""Demo-only adaptive MT5 auto-trade runner with closed-candle idempotency."""

from __future__ import annotations

import asyncio
import math
import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.auto_selection_routes import publish_auto_selection_status
from src.diagnostics.store import DiagnosticsStore
from src.trading.auto_selection import OHLCVBar
from src.trading.auto_trade.parameter_validator import (
    TradingParameterLimits,
    TradingParameterValidationService,
    TradingParameters,
)
from src.trading.auto_trade.signal_validator import DiagnosticSignalValidationService
from src.trading.auto_trade.strategy_runner import AdaptiveStrategyRunner, ExecutionMarketData, StrategyDecision
from src.trading.connectors.mt5 import _client
from src.trading.precision_execution import ACRTrailingStopService

router = APIRouter(prefix="/mt5/auto-trade", tags=["MT5 Auto Trade"])

# This is an execution-data sanity guard, not a strategy-quality filter. It is
# deliberately much wider than the old 100-point limit so normal XAUUSD
# spreads, including 25 pips, can still reach strategy evaluation.
_MAX_EXECUTION_SPREAD_POINTS = 1_000

_TIMEFRAMES = {
    "M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30", "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4",
}


class StartRequest(BaseModel):
    symbol: str = Field("XAUUSD", min_length=1, max_length=32)
    timeframe: str = Field("M5", pattern=r"^(M1|M5|M15|M30|H1|H4)$")
    lotSize: float = Field(0.01, ge=0.01, le=1)
    stopLossPips: float = Field(30, ge=5, le=250)
    takeProfitPips: float = Field(60, ge=10, le=500)
    paperMode: bool = True
    pollSeconds: float = Field(2, ge=1, le=30)


class RunnerStatus(BaseModel):
    running: bool
    state: str
    message: str
    symbol: str | None = None
    timeframe: str | None = None
    lastCandleAt: str | None = None
    lastDecision: str | None = None
    lastOrderId: str | None = None
    lastError: str | None = None
    selectedStrategyId: str | None = None
    decisionReason: str | None = None
    orderType: str | None = None
    entryPrice: float | None = None
    stopLoss: float | None = None
    takeProfit: float | None = None
    selectedEntryAreaType: str | None = None
    selectedEntryAreaId: str | None = None
    selectedEntryAreaLow: float | None = None
    selectedEntryAreaHigh: float | None = None
    selectedEntryAreaScore: float | None = None
    selectedEntryAreaReason: str | None = None
    entryAreaCandidates: list[dict[str, object]] = Field(default_factory=list)


@dataclass
class _State:
    running: bool = False
    state: str = "STOPPED"
    message: str = "Runner stopped"
    symbol: str | None = None
    timeframe: str | None = None
    last_candle_at: str | None = None
    last_decision: str | None = None
    last_order_id: str | None = None
    last_error: str | None = None
    last_candle_epoch: int | None = None
    selected_strategy_id: str | None = None
    decision_reason: str | None = None
    order_type: str | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    selected_entry_area_type: str | None = None
    selected_entry_area_id: str | None = None
    selected_entry_area_low: float | None = None
    selected_entry_area_high: float | None = None
    selected_entry_area_score: float | None = None
    selected_entry_area_reason: str | None = None
    entry_area_candidates: list[dict[str, object]] = field(default_factory=list)


class DemoAutoTradeRunner:
    def __init__(self) -> None:
        self._state = _State()
        self._task: asyncio.Task[None] | None = None
        self._lock = threading.RLock()

    def status(self) -> RunnerStatus:
        with self._lock:
            state = self._state
            return RunnerStatus(
                running=state.running, state=state.state, message=state.message,
                symbol=state.symbol, timeframe=state.timeframe,
                lastCandleAt=state.last_candle_at, lastDecision=state.last_decision,
                lastOrderId=state.last_order_id, lastError=state.last_error,
                selectedStrategyId=state.selected_strategy_id,
                decisionReason=state.decision_reason,
                orderType=state.order_type,
                entryPrice=state.entry_price,
                stopLoss=state.stop_loss,
                takeProfit=state.take_profit,
                selectedEntryAreaType=state.selected_entry_area_type,
                selectedEntryAreaId=state.selected_entry_area_id,
                selectedEntryAreaLow=state.selected_entry_area_low,
                selectedEntryAreaHigh=state.selected_entry_area_high,
                selectedEntryAreaScore=state.selected_entry_area_score,
                selectedEntryAreaReason=state.selected_entry_area_reason,
                entryAreaCandidates=state.entry_area_candidates,
            )

    async def start(self, request: StartRequest) -> RunnerStatus:
        if not request.paperMode:
            raise ValueError("Only Demo/Paper mode is supported by this runner")
        cfg = _client.load_config()
        if cfg.profile != "paper":
            raise ValueError("MT5 connector profile must be paper")
        baseline_epoch = await asyncio.to_thread(self._preflight, cfg, request)
        with self._lock:
            if self._state.running:
                raise RuntimeError("Runner is already active")
            self._state = _State(
                running=True, state="RUNNING", message="Waiting for an adaptive closed-candle setup",
                symbol=request.symbol.strip().upper(), timeframe=request.timeframe,
                last_candle_epoch=baseline_epoch,
            )
            self._task = asyncio.create_task(self._loop(cfg, request))
        return self.status()

    async def stop(self) -> RunnerStatus:
        with self._lock:
            task = self._task
            self._state.running = False
            self._state.state = "STOPPED"
            self._state.message = "Runner stopped; existing positions were not closed"
            self._task = None
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        return self.status()

    def _preflight(self, cfg: Any, request: StartRequest) -> int:
        with _client._session(cfg) as mt5:
            account = mt5.account_info()
            demo = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
            if getattr(account, "trade_mode", None) != demo:
                raise ValueError("Runner refuses non-demo MT5 accounts")
            name = _client._resolve_symbol(mt5, cfg, request.symbol)
            info = mt5.symbol_info(name)
            if info is None or not bool(getattr(info, "trade_allowed", True)):
                raise ValueError(f"Trading is unavailable for {name}")
            if mt5.symbol_info_tick(name) is None:
                raise ValueError(f"No live tick for {name}")
            timeframe = getattr(mt5, _TIMEFRAMES[request.timeframe])
            rates = mt5.copy_rates_from_pos(name, timeframe, 1, 1)
            if rates is None or len(rates) != 1:
                raise ValueError("No closed candle is available for baseline")
            return int(_value(rates[-1], "time"))

    async def _loop(self, cfg: Any, request: StartRequest) -> None:
        try:
            while self._state.running:
                try:
                    await asyncio.to_thread(self._cycle, cfg, request)
                except Exception as exc:  # fail closed; loop remains observable
                    with self._lock:
                        self._state.state = "ERROR"
                        self._state.last_error = str(exc)
                        self._state.message = f"Cycle failed: {exc}"
                await asyncio.sleep(request.pollSeconds)
        except asyncio.CancelledError:
            raise

    def _cycle(self, cfg: Any, request: StartRequest) -> None:
        with _client._session(cfg) as mt5:
            name = _client._resolve_symbol(mt5, cfg, request.symbol)
            timeframe = getattr(mt5, _TIMEFRAMES[request.timeframe])
            rates = mt5.copy_rates_from_pos(name, timeframe, 1, 128)
            if rates is None or len(rates) < 22:
                raise RuntimeError("At least 22 closed candles are required")
            latest_epoch = int(_value(rates[-1], "time"))
            with self._lock:
                if self._state.last_candle_epoch == latest_epoch:
                    return
                self._state.last_candle_epoch = latest_epoch
                self._state.last_candle_at = datetime.fromtimestamp(latest_epoch, timezone.utc).isoformat()

            info, tick, account = mt5.symbol_info(name), mt5.symbol_info_tick(name), mt5.account_info()
            if info is None or tick is None or account is None:
                raise RuntimeError("Symbol metadata, tick, or account data unavailable")
            point = float(getattr(info, "point", 0.01) or 0.01)
            spread_points = float(getattr(info, "spread", 0) or 0)
            if spread_points <= 0:
                raise RuntimeError("Spread data unavailable")
            bars = tuple(
                OHLCVBar(
                    timestamp=datetime.fromtimestamp(int(_value(row, "time")), timezone.utc),
                    open=float(_value(row, "open")),
                    high=float(_value(row, "high")),
                    low=float(_value(row, "low")),
                    close=float(_value(row, "close")),
                    volume=float(_value(row, "tick_volume")),
                )
                for row in rates
            )
            market = _market_data(info, account, point)
            session = _market_session(bars[-1].timestamp)
            with DiagnosticsStore() as diagnostics:
                decision = AdaptiveStrategyRunner(
                    name,
                    request.timeframe,
                    signal_validator=DiagnosticSignalValidationService(diagnostics),
                ).evaluate(
                    bars,
                    spread_pips=(spread_points * point) / market.pip_size,
                    session=session,
                    market=market,
                )
            publish_auto_selection_status(
                "default",
                decision.snapshot,
                decision.selection,
                session=session,
                spread_pips=(spread_points * point) / market.pip_size,
            )
            with self._lock:
                self._state.selected_strategy_id = decision.strategy_id
                self._state.decision_reason = decision.reason
                self._state.order_type = decision.order_type
                self._state.entry_price = decision.entry_price
                self._state.stop_loss = decision.stop_loss
                self._state.take_profit = decision.take_profit
                area = decision.selected_entry_area
                self._state.selected_entry_area_type = area.type if area else None
                self._state.selected_entry_area_id = area.id if area else None
                self._state.selected_entry_area_low = area.low if area else None
                self._state.selected_entry_area_high = area.high if area else None
                self._state.selected_entry_area_score = area.score if area else None
                self._state.selected_entry_area_reason = area.reason if area else None
                self._state.entry_area_candidates = [
                    {
                        "id": candidate.id,
                        "type": candidate.type,
                        "direction": candidate.direction,
                        "low": candidate.low,
                        "high": candidate.high,
                        "score": candidate.score,
                        "distance": candidate.distance,
                        "freshness": candidate.freshness,
                        "confluenceCount": candidate.confluence_count,
                        "reactionStatus": candidate.reaction_status,
                        "ageCandles": candidate.age_candles,
                        "mitigationCount": candidate.mitigation_count,
                        "reason": candidate.reason,
                    }
                    for candidate in decision.entry_area_candidates
                ]
                self._state.last_decision = decision.order_type or "HOLD"
                self._state.state = "RUNNING"
                self._state.last_error = None
                self._state.message = f"{decision.strategy_id or 'No strategy'}: {decision.reason}"
            positions = tuple(mt5.positions_get(symbol=name) or ())
            pending_orders = tuple(getattr(mt5, "orders_get", lambda **_kwargs: ())(symbol=name) or ())
            if positions or pending_orders:
                if pending_orders and self._should_cancel_pending(decision.reason):
                    self._cancel_pending_orders(mt5, name, pending_orders, decision.reason)
                updates = self._trail_positions(mt5, name, positions, decision, market)
                with self._lock:
                    self._state.message = (
                        "Existing position/pending order monitored; "
                        f"{updates} ACR trailing stop update(s) applied"
                    )
                return
            if not decision.executable:
                return
            self._submit(mt5, name, decision, request, info, tick, market)

    def _submit(
        self,
        mt5: Any,
        name: str,
        decision: StrategyDecision,
        request: StartRequest,
        info: Any,
        tick: Any,
        market: ExecutionMarketData,
    ) -> None:
        if not all((decision.direction, decision.entry_price, decision.stop_loss, decision.take_profit, decision.lot_size)):
            raise RuntimeError("Adaptive decision is incomplete")
        spread_points = float(getattr(info, "spread", 0) or 0)
        if (
            not math.isfinite(spread_points)
            or spread_points <= 0
            or spread_points > _MAX_EXECUTION_SPREAD_POINTS
        ):
            raise RuntimeError(f"Spread guard rejected {spread_points} points")
        is_buy = decision.direction == "BUY"
        market_order = decision.order_type in {"MARKET BUY", "MARKET SELL"}
        price = (
            float(getattr(tick, "ask" if is_buy else "bid", 0) or 0)
            if market_order else decision.entry_price
        )
        if price <= 0:
            raise RuntimeError("Invalid execution price")
        # Fixed Controls: lot/SL/TP from user settings, not risk-based/zona calc.
        # Strategy decides direction & entry; order levels = pip distance from entry.
        control_pip_size = _fixed_control_pip_size(name, market.pip_size)
        stop_loss, take_profit = _fixed_controls_levels(
            is_buy, price, control_pip_size, request.stopLossPips, request.takeProfitPips,
        )
        parameters = TradingParameterValidationService().validate(
            TradingParameters(
                symbol=name,
                timeframe=request.timeframe,
                side=decision.direction,
                lot_size=request.lotSize,
                entry_price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
            ),
            TradingParameterLimits(
                minimum_lot=market.minimum_lot,
                maximum_lot=market.maximum_lot,
                lot_step=market.lot_step,
            ),
        )
        payload = {
            "action": getattr(mt5, "TRADE_ACTION_DEAL", 1) if market_order else getattr(mt5, "TRADE_ACTION_PENDING", 5),
            "symbol": name,
            "volume": parameters.lot_size,
            "type": (
                getattr(mt5, "ORDER_TYPE_BUY", 0) if is_buy else getattr(mt5, "ORDER_TYPE_SELL", 1)
            ) if market_order else (
                getattr(mt5, "ORDER_TYPE_BUY_LIMIT", 2) if is_buy else getattr(mt5, "ORDER_TYPE_SELL_LIMIT", 3)
            ),
            "price": price, "sl": parameters.stop_loss, "tp": parameters.take_profit,
            "deviation": 20, "magic": 862001, "comment": "vibe-trading-auto",
            "type_time": getattr(mt5, "ORDER_TIME_GTC", 0),
            "type_filling": _filling_mode(mt5, info),
        }
        checked = mt5.order_check(payload)
        check_code = getattr(checked, "retcode", None) if checked is not None else None
        if check_code not in {0, getattr(mt5, "TRADE_RETCODE_DONE", 10009)}:
            self._log_execution(
                level="ERROR", status="REJECTED", symbol=name, decision=decision,
                parameters=parameters, error_code=str(check_code),
                message=f"order_check rejected: {check_code} {getattr(checked, 'comment', '')}",
            )
            raise RuntimeError(f"order_check rejected: {check_code} {getattr(checked, 'comment', '')}")
        result = mt5.order_send(payload)
        done = {getattr(mt5, "TRADE_RETCODE_DONE", 10009), getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010)}
        if result is None or getattr(result, "retcode", None) not in done:
            self._log_execution(
                level="ERROR", status="REJECTED", symbol=name, decision=decision,
                parameters=parameters, error_code=str(getattr(result, "retcode", None)),
                message=f"order_send rejected: {getattr(result, 'retcode', None)} {getattr(result, 'comment', '')}",
            )
            raise RuntimeError(f"order_send rejected: {getattr(result, 'retcode', None)} {getattr(result, 'comment', '')}")
        order_id = str(getattr(result, "order", "") or getattr(result, "deal", ""))
        with self._lock:
            self._state.last_order_id = order_id
            self._state.stop_loss = parameters.stop_loss
            self._state.take_profit = parameters.take_profit
            self._state.message = f"{decision.order_type} submitted; order {order_id}"
        self._log_execution(
            level="SIGNAL", status="EXECUTED", symbol=name, decision=decision,
            parameters=parameters, broker_order_id=order_id,
            message=f"{decision.order_type} executed; order {order_id}",
        )

    def _cancel_pending_orders(self, mt5: Any, name: str, orders: tuple[Any, ...], reason: str) -> int:
        cancelled = 0
        for order in orders:
            if str(getattr(order, "comment", "") or "") != "vibe-trading-auto":
                continue
            result = mt5.order_send({
                "action": getattr(mt5, "TRADE_ACTION_REMOVE", 8),
                "order": int(getattr(order, "ticket", 0) or 0),
                "symbol": name,
                "comment": f"auto-cancel: {reason[:80]}",
            })
            if result is not None and getattr(result, "retcode", None) in {
                getattr(mt5, "TRADE_RETCODE_DONE", 10009),
            }:
                cancelled += 1
        if cancelled:
            with self._lock:
                self._state.message = f"Cancelled {cancelled} pending setup order(s): {reason}"
        return cancelled

    @staticmethod
    def _should_cancel_pending(reason: str) -> bool:
        return any(
            marker in reason
            for marker in (
                "ACR zone is invalidated",
                "No fresh ACR zone",
                "No active FVG and ACR confluence",
                "Retest window expired",
                "Zone exceeded the maximum touch count",
                "HTF market structure does not confirm",
                "Range strategy requires neutral HTF market structure",
            )
        )

    def _trail_positions(
        self,
        mt5: Any,
        name: str,
        positions: tuple[Any, ...],
        decision: StrategyDecision,
        market: ExecutionMarketData,
    ) -> int:
        if not decision.acr_zones:
            return 0
        updates = 0
        for position in positions:
            is_buy = getattr(position, "type", None) == getattr(mt5, "POSITION_TYPE_BUY", 0)
            current_price = float(getattr(mt5.symbol_info_tick(name), "bid" if is_buy else "ask", 0) or 0)
            initial_stop = float(getattr(position, "sl", 0) or 0)
            opened_at = datetime.fromtimestamp(int(getattr(position, "time", 0) or 0), timezone.utc)
            if initial_stop <= 0 or current_price <= 0 or not int(getattr(position, "time", 0) or 0):
                continue
            plan = ACRTrailingStopService().calculate(
                direction="BUY" if is_buy else "SELL",
                initial_stop=initial_stop,
                current_price=current_price,
                opened_at=opened_at,
                zones=decision.acr_zones,
                pip_size=market.pip_size,
            )
            if plan.current_stop == initial_stop:
                continue
            result = mt5.order_send({
                "action": getattr(mt5, "TRADE_ACTION_SLTP", 6),
                "position": int(getattr(position, "ticket")),
                "symbol": name,
                "sl": plan.current_stop,
                "tp": float(getattr(position, "tp", 0) or 0),
            })
            if result is not None and getattr(result, "retcode", None) == getattr(mt5, "TRADE_RETCODE_DONE", 10009):
                updates += 1
        return updates

    @staticmethod
    def _log_execution(
        *,
        level: str,
        status: str,
        symbol: str,
        decision: StrategyDecision,
        parameters: TradingParameters | None = None,
        broker_order_id: str | None = None,
        error_code: str | None = None,
        message: str,
    ) -> None:
        """Persist one execution audit event so /auto-trade/execution-logs is never empty."""
        values: dict[str, object] = {
            "id": uuid.uuid4().hex[:16],
            "level": level,
            "status": status,
            "message": message[:1000],
            "symbol": symbol,
            "direction": decision.direction,
            "strategyId": decision.strategy_id,
            "lotSize": parameters.lot_size if parameters else decision.lot_size,
            "price": parameters.entry_price if parameters else decision.entry_price,
            "stopLoss": parameters.stop_loss if parameters else decision.stop_loss,
            "takeProfit": parameters.take_profit if parameters else decision.take_profit,
            "brokerOrderId": broker_order_id,
            "errorCode": error_code,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        try:
            with DiagnosticsStore() as store:
                store.append_auto_trade_execution_log(_USER_ID, values)
        except Exception:
            pass  # audit log must never break order submission flow


def _value(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        return getattr(row, key)


def _ema(values: list[float], period: int) -> float:
    """Kept as a deterministic utility for callers that used the former runner."""
    if len(values) < period or any(not math.isfinite(value) for value in values):
        raise ValueError("Invalid EMA input")
    result, alpha = sum(values[:period]) / period, 2.0 / (period + 1.0)
    for value in values[period:]:
        result = value * alpha + result * (1.0 - alpha)
    return result


def _market_data(info: Any, account: Any, point: float) -> ExecutionMarketData:
    tick_size = float(getattr(info, "trade_tick_size", 0) or point)
    tick_value = float(getattr(info, "trade_tick_value", 0) or 0)
    if tick_size <= 0 or tick_value <= 0:
        raise RuntimeError("Broker tick-size or tick-value metadata is unavailable")
    return ExecutionMarketData(
        balance=float(getattr(account, "balance", 0) or 0),
        tick_size=tick_size,
        tick_value_per_lot=tick_value,
        minimum_lot=float(getattr(info, "volume_min", 0.01) or 0.01),
        maximum_lot=float(getattr(info, "volume_max", 1.0) or 1.0),
        lot_step=float(getattr(info, "volume_step", 0.01) or 0.01),
        pip_size=point,
    )


def _market_session(timestamp: datetime) -> str:
    hour = timestamp.astimezone(timezone.utc).hour
    if 0 <= hour < 7:
        return "ASIA"
    if hour < 13:
        return "LONDON"
    if hour < 21:
        return "NEW_YORK"
    return "OFF_HOURS"


def _fixed_controls_levels(
    is_buy: bool, entry: float, pip_size: float, stop_loss_pips: float, take_profit_pips: float,
) -> tuple[float, float]:
    """Fixed Controls: SL/TP as pip distance from entry price."""
    sl_distance = pip_size * stop_loss_pips
    tp_distance = pip_size * take_profit_pips
    if is_buy:
        return round(entry - sl_distance, 8), round(entry + tp_distance, 8)
    return round(entry + sl_distance, 8), round(entry - tp_distance, 8)


def _fixed_control_pip_size(symbol: str, point: float) -> float:
    """Return the user-facing pip size without changing broker point semantics."""
    if point <= 0 or not math.isfinite(point):
        raise ValueError("point must be positive and finite")
    normalized = symbol.strip().upper()
    if "XAU" in normalized or "GOLD" in normalized:
        return point * 10.0
    return point


def _filling_mode(mt5: Any, info: Any) -> int:
    mask = int(getattr(info, "filling_mode", 0) or 0)
    if mask & int(getattr(mt5, "SYMBOL_FILLING_IOC", 2)):
        return getattr(mt5, "ORDER_FILLING_IOC", 1)
    if mask & int(getattr(mt5, "SYMBOL_FILLING_FOK", 1)):
        return getattr(mt5, "ORDER_FILLING_FOK", 0)
    return getattr(mt5, "ORDER_FILLING_RETURN", 2)


runner = DemoAutoTradeRunner()


@router.post("/start", response_model=RunnerStatus)
async def start(request: StartRequest) -> RunnerStatus:
    try:
        return await runner.start(request)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/stop", response_model=RunnerStatus)
async def stop() -> RunnerStatus:
    return await runner.stop()


@router.get("/status", response_model=RunnerStatus)
async def status() -> RunnerStatus:
    return runner.status()
_USER_ID = "user-123"  # demo-only single user; matches auto-trade config seed
