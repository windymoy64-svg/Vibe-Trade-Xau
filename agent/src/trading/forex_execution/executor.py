"""Runtime MT5 executor using an injected broker transport and no retries."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Callable, Protocol
from uuid import UUID

from src.trading.forex_decisions import ACTION, QuoteSnapshot
from src.trading.forex_execution.contracts import (
    BrokerCheckResult,
    BrokerExecutionResponse,
    ExecutionResult,
    ExecutionStatus,
    MT5TradingProfile,
    _canonical_json,
)
from src.trading.forex_risk import ApprovedOrderPlan, ApprovalStatus, SymbolSpecification
from src.trading.forex_signals.engine import _deterministic_uuid7


class BrokerTransport(Protocol):
    def refresh_quote(self, quote: QuoteSnapshot, profile: MT5TradingProfile) -> QuoteSnapshot: ...

    def refresh_symbol(
        self, specification: SymbolSpecification, profile: MT5TradingProfile
    ) -> SymbolSpecification: ...

    def order_check(self, request: dict[str, object], profile: MT5TradingProfile) -> BrokerCheckResult: ...

    def order_send(self, request: dict[str, object], profile: MT5TradingProfile) -> BrokerExecutionResponse: ...


class InvalidExecutionInputError(ValueError):
    pass


class DuplicateIntentError(InvalidExecutionInputError):
    pass


class DuplicateExecutionError(InvalidExecutionInputError):
    pass


class RuntimeMT5OrderExecutor:
    """Execute one approved plan through exactly one injected broker-send call."""

    def __init__(
        self,
        transport: BrokerTransport,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        stale_after_seconds: float = 120.0,
        done_retcodes: frozenset[int | str] = frozenset({0, 10009, "DONE"}),
        partial_retcodes: frozenset[int | str] = frozenset({10010, "DONE_PARTIAL", "PARTIAL"}),
        pending_retcodes: frozenset[int | str] = frozenset({10008, "PLACED", "PENDING"}),
    ) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        self._transport = transport
        self._clock = clock
        self._stale_after_seconds = stale_after_seconds
        self._done = done_retcodes
        self._partial = partial_retcodes
        self._pending = pending_retcodes
        self._seen_intents: set[UUID] = set()
        self._seen_plans: set[UUID] = set()
        self._seen_executions: set[UUID] = set()

    def execute(
        self,
        plan: ApprovedOrderPlan,
        specification: SymbolSpecification,
        quote: QuoteSnapshot,
        profile: MT5TradingProfile,
        position_ticket: int | None = None,
        position_side: str | None = None,
    ) -> ExecutionResult:
        now = self._now()
        quote = self._transport.refresh_quote(quote, profile)
        specification = self._transport.refresh_symbol(specification, profile)
        self._validate(plan, specification, quote, profile, now, position_ticket, position_side)
        if plan.intent_id in self._seen_intents:
            raise DuplicateIntentError("duplicate intent_id")
        if plan.order_plan_id in self._seen_plans:
            raise DuplicateExecutionError("duplicate order_plan_id")

        request = self._build_request(plan, specification, quote, profile, position_ticket, position_side)
        check = self._transport.order_check(request, profile)
        if not isinstance(check, BrokerCheckResult) or not check.passed:
            result = self._result(
                plan,
                ExecutionStatus.REJECTED,
                now,
                check.retcode if isinstance(check, BrokerCheckResult) else None,
                check.comment if isinstance(check, BrokerCheckResult) else "order_check failed",
                None,
                request,
            )
            self._consume(plan, result)
            return result

        response = self._transport.order_send(request, profile)
        if not isinstance(response, BrokerExecutionResponse):
            response = BrokerExecutionResponse(retcode=None, comment="unknown broker response")
        status = response.result_class or self._classify(response.retcode, response.filled_volume, plan.volume_lots)
        result = self._result(plan, status, now, response.retcode, response.comment, response, request)
        self._consume(plan, result)
        return result

    def replay(self, inputs):  # type: ignore[no-untyped-def]
        return tuple(self.execute(*item) for item in inputs)

    def _validate(self, plan, spec, quote, profile, now, position_ticket=None, position_side=None) -> None:  # type: ignore[no-untyped-def]
        if not isinstance(plan, ApprovedOrderPlan) or plan.approval_status is not ApprovalStatus.APPROVED:
            raise InvalidExecutionInputError("invalid ApprovedOrderPlan")
        if not isinstance(spec, SymbolSpecification) or not isinstance(quote, QuoteSnapshot) or not isinstance(profile, MT5TradingProfile):
            raise InvalidExecutionInputError("invalid executor input contract")
        if plan.action not in {action.value for action in (ACTION.OPEN_LONG, ACTION.OPEN_SHORT, ACTION.CLOSE_POSITION, ACTION.REVERSE_TO_LONG, ACTION.REVERSE_TO_SHORT)}:
            raise InvalidExecutionInputError("unsupported execution action")
        if plan.symbol != spec.symbol or plan.symbol != quote.symbol:
            raise InvalidExecutionInputError("symbol mismatch")
        if _stale(quote.broker_timestamp, now, self._stale_after_seconds):
            raise InvalidExecutionInputError("stale quote")
        if not spec.trading_enabled or not profile.trading_enabled:
            raise InvalidExecutionInputError("trading disabled")
        if not spec.market_available or not profile.market_available:
            raise InvalidExecutionInputError("market unavailable")
        if not spec.session_open or not profile.session_open:
            raise InvalidExecutionInputError("market closed")
        if quote.ask < quote.bid:
            raise InvalidExecutionInputError("invalid quote")
        if plan.action == ACTION.CLOSE_POSITION.value:
            if position_ticket is None:
                position_ticket = getattr(plan, "position_ticket", None)
            if not isinstance(position_ticket, int) or position_ticket <= 0:
                raise InvalidExecutionInputError("position ticket missing")
            if position_side is None:
                position_side = getattr(plan, "position_side", None)
            if not isinstance(position_side, str) or position_side.upper() not in {"LONG", "SHORT"}:
                raise InvalidExecutionInputError("position side missing")
        else:
            if plan.stop_loss is None or plan.take_profit is None or plan.entry_price is None:
                raise InvalidExecutionInputError("protective prices missing")
            distance = abs(plan.entry_price - plan.stop_loss)
            if distance < spec.stop_level_distance:
                raise InvalidExecutionInputError("stop level violation")
            if distance <= spec.freeze_level_distance:
                raise InvalidExecutionInputError("freeze level violation")
        if plan.expiration <= now:
            raise InvalidExecutionInputError("order plan expired")

    @staticmethod
    def _build_request(plan, spec, quote, profile, position_ticket=None, position_side=None) -> dict[str, object]:  # type: ignore[no-untyped-def]
        if plan.action == ACTION.CLOSE_POSITION.value:
            ticket = position_ticket if position_ticket is not None else getattr(plan, "position_ticket", None)
            current_side = position_side if position_side is not None else getattr(plan, "position_side", None)
            closing_long = current_side.upper() == "LONG"
            return {
                "symbol": plan.symbol,
                "action": plan.action,
                "side": "sell" if closing_long else "buy",
                "volume": plan.volume_lots,
                "price": quote.bid if closing_long else quote.ask,
                "position": ticket,
                "deviation": plan.max_slippage,
                "filling_mode": profile.filling_mode,
                "order_plan_id": str(plan.order_plan_id),
                "intent_id": str(plan.intent_id),
            }
        long_side = plan.action in {ACTION.OPEN_LONG.value, ACTION.REVERSE_TO_LONG.value}
        return {
            "symbol": plan.symbol,
            "action": plan.action,
            "side": "buy" if long_side else "sell",
            "volume": plan.volume_lots,
            "price": quote.ask if long_side else quote.bid,
            "stop_loss": plan.stop_loss,
            "take_profit": plan.take_profit,
            "deviation": plan.max_slippage,
            "filling_mode": profile.filling_mode,
            "execution_mode": profile.execution_mode,
            "expiration_policy": profile.expiration_policy,
            "stop_level_distance": spec.stop_level_distance,
            "freeze_level_distance": spec.freeze_level_distance,
            "order_plan_id": str(plan.order_plan_id),
            "intent_id": str(plan.intent_id),
        }

    def _result(self, plan, status, now, retcode, comment, response, request):  # type: ignore[no-untyped-def]
        order_ticket = response.order_ticket if response else None
        deal_ticket = response.deal_ticket if response else None
        position_ticket = response.position_ticket if response else None
        volume = response.filled_volume if response else 0.0
        price = response.filled_price if response else None
        material = {
            "action": plan.action,
            "broker_comment": comment,
            "broker_retcode": retcode,
            "execution_status": status.value,
            "filled_price": price,
            "filled_volume": volume,
            "intent_id": str(plan.intent_id),
            "order_plan_id": str(plan.order_plan_id),
            "position_ticket": position_ticket,
            "symbol": plan.symbol,
        }
        execution_id = _deterministic_uuid7(now, _canonical_json(material))
        replay_hash = hashlib.sha256(_canonical_json({**material, "execution_id": str(execution_id)}).encode("utf-8")).hexdigest()
        return ExecutionResult(
            execution_id=execution_id,
            order_plan_id=plan.order_plan_id,
            intent_id=plan.intent_id,
            symbol=plan.symbol,
            action=plan.action,
            execution_status=status,
            mt5_order_ticket=order_ticket,
            mt5_deal_ticket=deal_ticket,
            mt5_position_ticket=position_ticket,
            broker_retcode=retcode,
            broker_comment=comment,
            filled_volume=volume,
            filled_price=price,
            execution_time=now,
            replay_hash=replay_hash,
        )

    def _classify(self, retcode, filled_volume, requested):  # type: ignore[no-untyped-def]
        if retcode in self._done:
            return ExecutionStatus.FILLED
        if retcode in self._partial or 0 < filled_volume < requested:
            return ExecutionStatus.PARTIALLY_FILLED
        if retcode in self._pending:
            return ExecutionStatus.PENDING
        if retcode is None:
            return ExecutionStatus.UNKNOWN
        return ExecutionStatus.REJECTED

    def _consume(self, plan: ApprovedOrderPlan, result: ExecutionResult) -> None:
        if result.execution_id in self._seen_executions:
            raise DuplicateExecutionError("duplicate execution_id")
        self._seen_intents.add(plan.intent_id)
        self._seen_plans.add(plan.order_plan_id)
        self._seen_executions.add(result.execution_id)

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("executor clock must be timezone-aware")
        return value.astimezone(timezone.utc)


def _stale(timestamp: datetime, now: datetime, seconds: float) -> bool:
    age = (now - timestamp).total_seconds()
    return age < 0 or age > seconds
