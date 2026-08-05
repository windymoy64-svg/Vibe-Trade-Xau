"""Demo-only MT5 auto-trade runner with closed-candle idempotency."""

from __future__ import annotations

import asyncio
import math
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.trading.connectors.mt5 import _client

router = APIRouter(prefix="/mt5/auto-trade", tags=["MT5 Auto Trade"])

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
                running=True, state="RUNNING", message="Waiting for a closed-candle EMA crossover",
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
            rates = mt5.copy_rates_from_pos(name, timeframe, 1, 64)
            if rates is None or len(rates) < 22:
                raise RuntimeError("At least 22 closed candles are required")
            latest_epoch = int(_value(rates[-1], "time"))
            with self._lock:
                if self._state.last_candle_epoch == latest_epoch:
                    return
                self._state.last_candle_epoch = latest_epoch
                self._state.last_candle_at = datetime.fromtimestamp(latest_epoch, timezone.utc).isoformat()

            closes = [float(_value(row, "close")) for row in rates]
            previous_fast, latest_fast = _ema(closes[:-1], 9), _ema(closes, 9)
            previous_slow, latest_slow = _ema(closes[:-1], 21), _ema(closes, 21)
            decision = (
                "BUY" if previous_fast <= previous_slow and latest_fast > latest_slow else
                "SELL" if previous_fast >= previous_slow and latest_fast < latest_slow else "HOLD"
            )
            with self._lock:
                self._state.last_decision = decision
                self._state.state = "RUNNING"
                self._state.last_error = None
                self._state.message = f"Closed candle evaluated: {decision}"
            if decision == "HOLD":
                return
            if tuple(mt5.positions_get(symbol=name) or ()):
                with self._lock:
                    self._state.message = "Signal blocked: a position is already open"
                return
            self._submit(mt5, name, decision, request)

    def _submit(self, mt5: Any, name: str, decision: str, request: StartRequest) -> None:
        info, tick = mt5.symbol_info(name), mt5.symbol_info_tick(name)
        if info is None or tick is None:
            raise RuntimeError("Symbol metadata or tick unavailable")
        point = float(getattr(info, "point", 0.01) or 0.01)
        spread_points = float(getattr(info, "spread", 0) or 0)
        if spread_points <= 0 or spread_points > 100:
            raise RuntimeError(f"Spread guard rejected {spread_points} points")
        is_buy = decision == "BUY"
        price = float(getattr(tick, "ask" if is_buy else "bid", 0) or 0)
        if price <= 0:
            raise RuntimeError("Invalid execution price")
        sl_distance, tp_distance = request.stopLossPips * point, request.takeProfitPips * point
        payload = {
            "action": getattr(mt5, "TRADE_ACTION_DEAL", 1), "symbol": name,
            "volume": request.lotSize,
            "type": getattr(mt5, "ORDER_TYPE_BUY", 0) if is_buy else getattr(mt5, "ORDER_TYPE_SELL", 1),
            "price": price, "sl": price - sl_distance if is_buy else price + sl_distance,
            "tp": price + tp_distance if is_buy else price - tp_distance,
            "deviation": 20, "magic": 862001, "comment": "vibe-trading-auto",
            "type_time": getattr(mt5, "ORDER_TIME_GTC", 0),
            "type_filling": _filling_mode(mt5, info),
        }
        checked = mt5.order_check(payload)
        check_code = getattr(checked, "retcode", None) if checked is not None else None
        if check_code not in {0, getattr(mt5, "TRADE_RETCODE_DONE", 10009)}:
            raise RuntimeError(f"order_check rejected: {check_code} {getattr(checked, 'comment', '')}")
        result = mt5.order_send(payload)
        done = {getattr(mt5, "TRADE_RETCODE_DONE", 10009), getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010)}
        if result is None or getattr(result, "retcode", None) not in done:
            raise RuntimeError(f"order_send rejected: {getattr(result, 'retcode', None)} {getattr(result, 'comment', '')}")
        with self._lock:
            self._state.last_order_id = str(getattr(result, "order", "") or getattr(result, "deal", ""))
            self._state.message = f"{decision} filled; order {self._state.last_order_id}"


def _value(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        return getattr(row, key)


def _ema(values: list[float], period: int) -> float:
    if len(values) < period or any(not math.isfinite(value) for value in values):
        raise ValueError("Invalid EMA input")
    result, alpha = sum(values[:period]) / period, 2.0 / (period + 1.0)
    for value in values[period:]:
        result = value * alpha + result * (1.0 - alpha)
    return result


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