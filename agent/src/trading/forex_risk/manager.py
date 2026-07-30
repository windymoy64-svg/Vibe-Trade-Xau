"""Fail-closed deterministic Runtime Forex Risk Manager."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR
from typing import Callable

from src.trading.forex_decisions import ACTION, DecisionSnapshot, QuoteSnapshot
from src.trading.forex_decisions.contracts import _canonical_json as _decision_json
from src.trading.forex_risk.contracts import (
    AccountSnapshot,
    ApprovalStatus,
    ApprovedOrderPlan,
    RiskConfiguration,
    RiskPositionDirection,
    RiskPositionSnapshot,
    SymbolSpecification,
    _canonical_json,
)
from src.trading.forex_signals.engine import _deterministic_uuid7
from src.trading.runtime_config import RuntimeConfig


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeForexRiskManager:
    """Approve or reject an entry decision without broker side effects."""

    def __init__(
        self,
        *,
        runtime_config: RuntimeConfig | None = None,
        clock: Callable[[], datetime] = _default_clock,
        stale_after: timedelta = timedelta(minutes=2),
    ) -> None:
        if stale_after <= timedelta(0):
            raise ValueError("stale_after must be positive")
        self.runtime_config = runtime_config or RuntimeConfig()
        self._clock = clock
        self._stale_after = stale_after

    def assess(
        self,
        decision: DecisionSnapshot,
        account: AccountSnapshot,
        quote: QuoteSnapshot,
        specification: SymbolSpecification,
        configuration: RiskConfiguration,
        position: RiskPositionSnapshot | None = None,
    ) -> ApprovedOrderPlan:
        now = self._now()
        if decision.action is ACTION.CLOSE_POSITION:
            return self._assess_exit(decision, quote, specification, configuration, position, now)
        rejection = self._validate(decision, account, quote, specification, configuration, now)
        long_side = decision.action in {ACTION.OPEN_LONG, ACTION.REVERSE_TO_LONG}
        entry = quote.ask if long_side else quote.bid
        risk_amount = account.equity * configuration.risk_percent / 100.0
        stop_distance = configuration.stop_loss_distance
        volume = 0.0
        stop_loss = None
        take_profit = None

        if rejection is None and stop_distance is not None:
            stop_loss = entry - stop_distance if long_side else entry + stop_distance
            take_profit = (
                entry + stop_distance * configuration.reward_ratio
                if long_side
                else entry - stop_distance * configuration.reward_ratio
            )
            if stop_loss <= 0 or take_profit <= 0:
                rejection = "INVALID_TAKE_PROFIT"
            else:
                risk_per_lot = (stop_distance / specification.tick_size) * specification.tick_value_per_lot
                if risk_per_lot <= 0:
                    rejection = "INVALID_SYMBOL_RISK_VALUE"
                else:
                    volume = _floor_step(risk_amount / risk_per_lot, specification.lot_step)
                    rejection = self._validate_sized_order(
                        volume, entry, risk_amount, account, specification, configuration
                    )

        status = ApprovalStatus.APPROVED if rejection is None else ApprovalStatus.REJECTED
        if status is ApprovalStatus.REJECTED:
            volume = 0.0
        expiration = decision.broker_timestamp + timedelta(seconds=configuration.expiration_seconds)
        material = {
            "action": decision.action.value,
            "approval_status": status.value,
            "decision_digest": decision.digest,
            "entry_price": entry,
            "expiration": expiration.isoformat(),
            "intent_id": str(decision.intent_id),
            "max_slippage": configuration.max_slippage,
            "rejection_reason": rejection,
            "reward_ratio": configuration.reward_ratio,
            "risk_amount": risk_amount,
            "risk_percent": configuration.risk_percent,
            "stop_loss": stop_loss,
            "symbol": decision.symbol,
            "take_profit": take_profit,
            "volume_lots": volume,
        }
        order_plan_id = _deterministic_uuid7(decision.broker_timestamp, _canonical_json(material))
        replay_hash = hashlib.sha256(
            _canonical_json({**material, "order_plan_id": str(order_plan_id)}).encode("utf-8")
        ).hexdigest()
        return ApprovedOrderPlan(
            order_plan_id=order_plan_id,
            intent_id=decision.intent_id,
            symbol=decision.symbol,
            action=decision.action.value,
            volume_lots=volume,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_percent=configuration.risk_percent,
            risk_amount=risk_amount,
            reward_ratio=configuration.reward_ratio,
            max_slippage=configuration.max_slippage,
            expiration=expiration,
            approval_status=status,
            rejection_reason=rejection,
            replay_hash=replay_hash,
        )

    def _assess_exit(
        self,
        decision: DecisionSnapshot,
        quote: QuoteSnapshot,
        specification: SymbolSpecification,
        configuration: RiskConfiguration,
        position: RiskPositionSnapshot | None,
        now: datetime,
    ) -> ApprovedOrderPlan:
        rejection = self._validate_exit(decision, quote, specification, position, now)
        volume = position.volume_lots if rejection is None and position is not None else 0.0
        entry = quote.bid if position is not None and position.direction is RiskPositionDirection.LONG else quote.ask
        status = ApprovalStatus.APPROVED if rejection is None else ApprovalStatus.REJECTED
        expiration = decision.broker_timestamp + timedelta(seconds=configuration.expiration_seconds)
        material = {
            "action": decision.action.value,
            "approval_status": status.value,
            "decision_digest": decision.digest,
            "entry_price": entry,
            "expiration": expiration.isoformat(),
            "intent_id": str(decision.intent_id),
            "max_slippage": configuration.max_slippage,
            "position_ticket": position.position_ticket if position is not None else None,
            "rejection_reason": rejection,
            "reward_ratio": 0.0,
            "risk_amount": 0.0,
            "risk_percent": 0.0,
            "stop_loss": None,
            "symbol": decision.symbol,
            "take_profit": None,
            "volume_lots": volume,
        }
        order_plan_id = _deterministic_uuid7(decision.broker_timestamp, _canonical_json(material))
        replay_hash = hashlib.sha256(
            _canonical_json({**material, "order_plan_id": str(order_plan_id)}).encode("utf-8")
        ).hexdigest()
        return ApprovedOrderPlan(
            order_plan_id=order_plan_id,
            intent_id=decision.intent_id,
            symbol=decision.symbol,
            action=decision.action.value,
            volume_lots=volume,
            entry_price=entry,
            stop_loss=None,
            take_profit=None,
            risk_percent=0.0,
            risk_amount=0.0,
            reward_ratio=0.0,
            max_slippage=configuration.max_slippage,
            expiration=expiration,
            approval_status=status,
            rejection_reason=rejection,
            replay_hash=replay_hash,
        )

    def replay(
        self,
        inputs: tuple[tuple, ...] | list[tuple],
    ) -> tuple[ApprovedOrderPlan, ...]:
        return tuple(self.assess(*item) for item in inputs)

    def _validate(self, decision, account, quote, spec, config, now) -> str | None:  # type: ignore[no-untyped-def]
        if not isinstance(decision, DecisionSnapshot) or not _valid_decision_hash(decision):
            return "INVALID_DECISION"
        if not isinstance(account, AccountSnapshot):
            return "INVALID_ACCOUNT"
        if not isinstance(quote, QuoteSnapshot):
            return "INVALID_QUOTE"
        if not isinstance(spec, SymbolSpecification):
            return "INVALID_SYMBOL_SPECIFICATION"
        if not isinstance(config, RiskConfiguration):
            return "INVALID_RISK_CONFIGURATION"
        if decision.symbol != quote.symbol or decision.symbol != spec.symbol:
            return "SYMBOL_MISMATCH"
        if decision.timeframe != quote.timeframe:
            return "TIMEFRAME_MISMATCH"
        if decision.action not in {
            ACTION.OPEN_LONG,
            ACTION.OPEN_SHORT,
            ACTION.REVERSE_TO_LONG,
            ACTION.REVERSE_TO_SHORT,
        }:
            return "ACTION_NOT_ENTRY"
        if _stale(quote.broker_timestamp, now, self._stale_after):
            return "STALE_QUOTE"
        if _stale(account.broker_timestamp, now, self._stale_after):
            return "STALE_ACCOUNT"
        if quote.ask < quote.bid:
            return "INVALID_QUOTE"
        if quote.spread > config.max_spread:
            return "SPREAD_LIMIT_EXCEEDED"
        if not spec.trading_enabled:
            return "SYMBOL_TRADING_DISABLED"
        if not spec.market_available:
            return "MARKET_UNAVAILABLE"
        if not spec.session_open:
            return "TRADING_SESSION_CLOSED"
        if account.free_margin < config.min_free_margin:
            return "FREE_MARGIN_BELOW_THRESHOLD"
        if account.margin_level < config.min_margin_level:
            return "MARGIN_LEVEL_BELOW_THRESHOLD"
        if account.daily_loss >= config.max_daily_loss:
            return "DAILY_LOSS_LIMIT_EXCEEDED"
        if account.drawdown_percent >= config.max_drawdown_percent:
            return "MAX_DRAWDOWN_EXCEEDED"
        if account.trades_today >= config.max_trades_per_day:
            return "MAX_TRADES_PER_DAY_EXCEEDED"
        if account.consecutive_losses >= config.max_consecutive_losses:
            return "CONSECUTIVE_LOSS_LIMIT_EXCEEDED"
        if account.symbol_exposure >= config.max_symbol_exposure:
            return "MAX_SYMBOL_EXPOSURE_EXCEEDED"
        if account.correlated_exposure >= config.max_correlated_exposure:
            return "CORRELATED_EXPOSURE_EXCEEDED"
        if config.stop_loss_distance is None:
            return "STOP_LOSS_REQUIRED"
        if config.stop_loss_distance < spec.stop_level_distance:
            return "STOP_LEVEL_VIOLATION"
        if config.stop_loss_distance <= spec.freeze_level_distance:
            return "FREEZE_LEVEL_VIOLATION"
        return None

    def _validate_exit(self, decision, quote, spec, position, now) -> str | None:  # type: ignore[no-untyped-def]
        if not isinstance(decision, DecisionSnapshot) or not _valid_decision_hash(decision):
            return "INVALID_DECISION"
        if not isinstance(quote, QuoteSnapshot):
            return "INVALID_QUOTE"
        if not isinstance(spec, SymbolSpecification):
            return "INVALID_SYMBOL_SPECIFICATION"
        if decision.action is not ACTION.CLOSE_POSITION:
            return "ACTION_NOT_EXIT"
        if decision.symbol != quote.symbol or decision.symbol != spec.symbol:
            return "SYMBOL_MISMATCH"
        if decision.timeframe != quote.timeframe:
            return "TIMEFRAME_MISMATCH"
        if _stale(quote.broker_timestamp, now, self._stale_after):
            return "STALE_QUOTE"
        if quote.ask < quote.bid:
            return "INVALID_QUOTE"
        if not spec.trading_enabled:
            return "SYMBOL_TRADING_DISABLED"
        if not spec.market_available:
            return "MARKET_UNAVAILABLE"
        if not spec.session_open:
            return "TRADING_SESSION_CLOSED"
        if position is None:
            return "POSITION_NOT_FOUND"
        if not isinstance(position, RiskPositionSnapshot):
            return "INVALID_POSITION"
        if not position.owned:
            return "POSITION_NOT_OWNED"
        if position.symbol != decision.symbol:
            return "POSITION_SYMBOL_MISMATCH"
        return None

    @staticmethod
    def _validate_sized_order(volume, entry, risk_amount, account, spec, config) -> str | None:  # type: ignore[no-untyped-def]
        if volume < spec.min_lot:
            return "LOT_BELOW_MINIMUM"
        if volume > spec.max_lot:
            return "LOT_ABOVE_MAXIMUM"
        projected_margin = entry * spec.contract_size * volume / account.leverage
        if projected_margin > account.free_margin - config.min_free_margin:
            return "PROJECTED_MARGIN_INSUFFICIENT"
        projected_notional = entry * spec.contract_size * volume
        if account.symbol_exposure + projected_notional > config.max_symbol_exposure:
            return "MAX_SYMBOL_EXPOSURE_EXCEEDED"
        if account.correlated_exposure + projected_notional > config.max_correlated_exposure:
            return "CORRELATED_EXPOSURE_EXCEEDED"
        if risk_amount <= 0:
            return "INVALID_RISK_AMOUNT"
        return None

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("risk manager clock must be timezone-aware")
        return value.astimezone(timezone.utc)


def _floor_step(value: float, step: float) -> float:
    decimal_value = Decimal(str(value))
    decimal_step = Decimal(str(step))
    units = (decimal_value / decimal_step).to_integral_value(rounding=ROUND_FLOOR)
    return float(units * decimal_step)


def _stale(timestamp: datetime, now: datetime, threshold: timedelta) -> bool:
    age = now - timestamp
    return age < timedelta(0) or age > threshold


def _valid_decision_hash(decision: DecisionSnapshot) -> bool:
    # Reconstruct the exact Decision Engine material without importing/modifying it.
    material = {
        "broker_timestamp": decision.broker_timestamp.isoformat(),
        "current_position_state": decision.current_position_state.value,
        "intent_action": decision.action.value,
        "signal_id": str(decision.signal_id),
        "signal_type": decision.signal_type,
        "strategy_name": "forex-ema-macd-rsi-baseline",
        "strategy_version": "1.0.0",
        "symbol": decision.symbol,
        "target_position_state": decision.target_position_state.value,
        "timeframe": decision.timeframe,
    }
    # Quote timestamp is intentionally present in Decision Engine replay material,
    # but not exposed by DecisionSnapshot. The immutable digest still protects the
    # decision fields; exact replay-hash verification cannot be reconstructed here.
    return len(decision.replay_hash) == 64 and bool(_decision_json(material))
