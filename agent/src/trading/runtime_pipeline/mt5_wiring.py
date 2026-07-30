"""Injected production wiring between MT5 structures and runtime contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from src.trading.forex_decisions import PendingOrdersState, PositionState, PositionStateSnapshot, QuoteSnapshot, StrategyRuntimeState
from src.trading.forex_execution import BrokerCheckResult, BrokerExecutionResponse, MT5TradingProfile
from src.trading.forex_positions import (
    DealEntry, DealHistorySnapshot, Direction, MT5PositionEntry, MT5PositionSnapshot,
    PendingOrderEntry, PendingOrdersSnapshot,
)
from src.trading.forex_risk import (
    AccountSnapshot, RiskPositionDirection, RiskPositionSnapshot, SymbolSpecification,
)


def _get(value: object, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _time(value: Any, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value is None:
        return fallback
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


class MT5BrokerTransport:
    """BrokerTransport backed by one injected MT5-compatible API object."""

    def __init__(self, api: object, *, magic_number: int = 862001, comment: str = "vibe-trading",
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.api = api
        self.magic_number = magic_number
        self.comment = comment
        self.clock = clock

    def refresh_quote(self, quote: QuoteSnapshot, profile: MT5TradingProfile) -> QuoteSnapshot:
        tick = self.api.symbol_info_tick(quote.symbol)  # type: ignore[attr-defined]
        if tick is None:
            return quote
        return quote.model_copy(update={
            "bid": float(_get(tick, "bid", quote.bid)), "ask": float(_get(tick, "ask", quote.ask)),
            "broker_timestamp": _time(_get(tick, "time", None), quote.broker_timestamp),
            "spread": float(_get(tick, "spread", quote.spread)),
        })

    def refresh_symbol(self, specification: SymbolSpecification, profile: MT5TradingProfile) -> SymbolSpecification:
        info = self.api.symbol_info(specification.symbol)  # type: ignore[attr-defined]
        if info is None:
            return specification
        return specification.model_copy(update={
            "trading_enabled": bool(_get(info, "trade_allowed", specification.trading_enabled)),
            "tick_size": float(_get(info, "trade_tick_size", specification.tick_size)),
            "contract_size": float(_get(info, "trade_contract_size", specification.contract_size)),
            "lot_step": float(_get(info, "volume_step", specification.lot_step)),
            "min_lot": float(_get(info, "volume_min", specification.min_lot)),
            "max_lot": float(_get(info, "volume_max", specification.max_lot)),
            "stop_level_distance": float(_get(info, "trade_stops_level", specification.stop_level_distance)),
            "freeze_level_distance": float(_get(info, "trade_freeze_level", specification.freeze_level_distance)),
        })

    def order_check(self, request: dict[str, object], profile: MT5TradingProfile) -> BrokerCheckResult:
        raw = self.api.order_check(self._mt5_request(request))  # type: ignore[attr-defined]
        if raw is None:
            return BrokerCheckResult(passed=False, comment="order_check returned no result")
        code = _get(raw, "retcode", None)
        return BrokerCheckResult(passed=code in (0, 10009, "DONE"), retcode=code, comment=str(_get(raw, "comment", "")))

    def order_send(self, request: dict[str, object], profile: MT5TradingProfile) -> BrokerExecutionResponse:
        raw = self.api.order_send(self._mt5_request(request))  # type: ignore[attr-defined]
        return BrokerExecutionResponse(
            retcode=_get(raw, "retcode", None), comment=str(_get(raw, "comment", "")),
            order_ticket=_get(raw, "order", _get(raw, "order_ticket", None)),
            deal_ticket=_get(raw, "deal", _get(raw, "deal_ticket", None)),
            position_ticket=_get(raw, "position", _get(raw, "position_ticket", None)),
            filled_volume=float(_get(raw, "volume", _get(raw, "filled_volume", 0.0)) or 0.0),
            filled_price=_get(raw, "price", _get(raw, "filled_price", None)),
        )

    def _mt5_request(self, request: dict[str, object]) -> dict[str, object]:
        original_deviation = request["deviation"]
        translated_deviation = int(float(original_deviation))
        print(f"Runtime max_slippage : {original_deviation}")
        print(f"MT5 deviation : {translated_deviation}")
        print(f"Python type : {type(translated_deviation).__name__}")
        translated: dict[str, object] = {
            "action": getattr(self.api, "TRADE_ACTION_DEAL", 1),
            "symbol": request["symbol"], "volume": request["volume"], "price": request["price"],
            "type": getattr(self.api, "ORDER_TYPE_BUY", 0) if request["side"] == "buy" else getattr(self.api, "ORDER_TYPE_SELL", 1),
            "deviation": translated_deviation, "type_filling": self._filling_mode(request["filling_mode"]),
            "magic": self.magic_number, "comment": self.comment,
        }
        if request.get("position") is not None:
            translated["position"] = request["position"]
        if request.get("stop_loss") is not None:
            translated["sl"] = request["stop_loss"]
        if request.get("take_profit") is not None:
            translated["tp"] = request["take_profit"]
        return translated

    def _filling_mode(self, value: object) -> object:
        name = str(value).strip().upper()
        return getattr(self.api, f"ORDER_FILLING_{name}", value)


class MT5RuntimeInputs:
    """Read-only MT5-to-runtime mapping seam; all dependencies are injected."""

    def __init__(self, api: object, *, specification: SymbolSpecification, profile: MT5TradingProfile,
                 strategy_state: StrategyRuntimeState | None = None,
                 strategy_name: str = "forex-ema-macd-rsi-baseline", strategy_version: str = "1.0.0",
                 magic_number: int = 862001, comment_prefix: str = "vibe-trading",
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.api, self.specification, self.profile = api, specification, profile
        self.strategy_state = strategy_state or StrategyRuntimeState(strategy_name=strategy_name, strategy_version=strategy_version)
        self.strategy_name, self.strategy_version = strategy_name, strategy_version
        self.magic_number, self.comment_prefix = magic_number, comment_prefix
        self.clock = clock
        self._last_execution = None

    def _position_rows(self) -> tuple[object, ...]:
        return tuple(self.api.positions_get(symbol=self.specification.symbol) or ())  # type: ignore[attr-defined]

    def _quote(self) -> QuoteSnapshot:
        tick = self.api.symbol_info_tick(self.specification.symbol)  # type: ignore[attr-defined]
        now = self.clock()
        return QuoteSnapshot(symbol=self.specification.symbol, timeframe="1h", broker_timestamp=_time(_get(tick, "time", None), now),
                             bid=float(_get(tick, "bid", 0.0)), ask=float(_get(tick, "ask", 0.0)), spread=float(_get(tick, "spread", 0.0)))

    def _position_risk(self) -> RiskPositionSnapshot | None:
        row = next(iter(self._position_rows()), None)
        if row is None:
            return None
        side = int(_get(row, "type", 0))
        return RiskPositionSnapshot(symbol=self.specification.symbol, position_ticket=int(_get(row, "ticket")),
                                    direction=RiskPositionDirection.LONG if side == 0 else RiskPositionDirection.SHORT,
                                    volume_lots=float(_get(row, "volume", 0.0)), owned=True)

    def decision_inputs(self, market_snapshot: object):
        position = self._position_risk()
        state = PositionState.FLAT if position is None else (PositionState.LONG if position.direction is RiskPositionDirection.LONG else PositionState.SHORT)
        return PositionStateSnapshot(symbol=self.specification.symbol, state=state), PendingOrdersState(symbol=self.specification.symbol), self._quote(), self.strategy_state

    def risk_inputs(self, market_snapshot: object):
        account = self.api.account_info()  # type: ignore[attr-defined]
        return self._account(account), self._quote(), self.specification

    def current_position(self, market_snapshot: object) -> RiskPositionSnapshot | None:
        return self._position_risk()

    def execution_profile(self, market_snapshot: object) -> MT5TradingProfile:
        return self.profile

    def forward_execution(self, result) -> None:  # type: ignore[no-untyped-def]
        self._last_execution = result

    def update_position_state(self, market_snapshot: object):
        return PositionStateSnapshot(symbol=self.specification.symbol, state=PositionState.FLAT if self._position_risk() is None else PositionState.LONG)

    def position_evidence(self, market_snapshot: object):
        now = self.clock()
        positions = tuple(self._position_entry(row, now) for row in self._position_rows())
        orders = tuple(self._order_entry(row, now) for row in (self.api.orders_get(symbol=self.specification.symbol) or ()))  # type: ignore[attr-defined]
        deals = tuple(self._deal_entry(row, now) for row in (self.api.history_deals_get(datetime.fromtimestamp(0, timezone.utc), now, group=self.specification.symbol) or ()))  # type: ignore[attr-defined]
        return (MT5PositionSnapshot(captured_at=now, positions=positions),
                PendingOrdersSnapshot(captured_at=now, orders=orders),
                DealHistorySnapshot(captured_at=now, deals=deals))

    def _account(self, raw: object) -> AccountSnapshot:
        return AccountSnapshot(broker_timestamp=_time(_get(raw, "time", None), self.clock()), equity=float(_get(raw, "equity", 0)),
            free_margin=float(_get(raw, "margin_free", 0)), margin_level=float(_get(raw, "margin_level", 0)), leverage=float(_get(raw, "leverage", 1)),
            daily_loss=0, drawdown_percent=0, trades_today=0, consecutive_losses=0, symbol_exposure=0, correlated_exposure=0)

    def _position_entry(self, row: object, now: datetime) -> MT5PositionEntry:
        direction = Direction.LONG if int(_get(row, "type", 0)) == 0 else Direction.SHORT
        intent_id = self._intent_for(_get(row, "ticket", None), _get(row, "order", None), _get(row, "deal", None))
        return MT5PositionEntry(symbol=self.specification.symbol, magic_number=int(_get(row, "magic", self.magic_number)),
            comment=str(_get(row, "comment", self.comment_prefix)), strategy_name=self.strategy_name, strategy_version=self.strategy_version,
            intent_id=intent_id, ticket=int(_get(row, "ticket")), order_ticket=_get(row, "order", None), deal_ticket=_get(row, "deal", None), direction=direction,
            volume_lots=float(_get(row, "volume", 0)), entry_price=float(_get(row, "price_open", 0)), stop_loss=_get(row, "sl", None), take_profit=_get(row, "tp", None), open_time=_time(_get(row, "time", None), now), update_time=now)

    def _order_entry(self, row: object, now: datetime) -> PendingOrderEntry:
        direction = Direction.LONG if int(_get(row, "type", 0)) in {0, 2, 4, 6} else Direction.SHORT
        volume = float(_get(row, "volume_initial", _get(row, "volume_current", 0)))
        return PendingOrderEntry(symbol=self.specification.symbol, magic_number=int(_get(row, "magic", self.magic_number)),
            comment=str(_get(row, "comment", self.comment_prefix)), strategy_name=self.strategy_name, strategy_version=self.strategy_version,
            intent_id=self._intent_for(None, _get(row, "ticket", None), None), ticket=int(_get(row, "ticket")), direction=direction, requested_volume=volume,
            remaining_volume=float(_get(row, "volume_current", volume)), setup_time=_time(_get(row, "time_setup", None), now))

    def _deal_entry(self, row: object, now: datetime) -> DealEntry:
        direction = Direction.LONG if int(_get(row, "type", 0)) == 0 else Direction.SHORT
        return DealEntry(symbol=self.specification.symbol, magic_number=int(_get(row, "magic", self.magic_number)),
            comment=str(_get(row, "comment", self.comment_prefix)), strategy_name=self.strategy_name, strategy_version=self.strategy_version,
            intent_id=self._intent_for(_get(row, "position_id", None), _get(row, "order", None), _get(row, "ticket", None)), ticket=int(_get(row, "ticket")), order_ticket=int(_get(row, "order")),
            position_ticket=_get(row, "position_id", None), direction=direction, volume_lots=float(_get(row, "volume", 0)),
            price=float(_get(row, "price", 0)), is_exit=int(_get(row, "entry", 0)) != 0,
            deal_time=_time(_get(row, "time", None), now))

    def _intent_for(self, position_ticket: Any, order_ticket: Any, deal_ticket: Any):  # type: ignore[no-untyped-def]
        result = self._last_execution
        if result is None:
            return None
        if any(ticket is not None and int(ticket) == expected for ticket, expected in (
            (position_ticket, result.mt5_position_ticket), (order_ticket, result.mt5_order_ticket),
            (deal_ticket, result.mt5_deal_ticket),
        ) if expected is not None):
            return result.intent_id
        return None
