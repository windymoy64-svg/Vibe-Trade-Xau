"""End-to-end deterministic runtime forex pipeline runner."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Iterable, Protocol

from src.trading.forex_decisions import ACTION, RuntimeDecisionEngine
from src.trading.forex_execution import ExecutionResult, MT5TradingProfile, RuntimeMT5OrderExecutor
from src.trading.forex_features import DuplicateBarError, RuntimeFeatureBuilder, WarmupStatus
from src.trading.forex_positions import (
    DealHistorySnapshot,
    MT5PositionSnapshot,
    PendingOrdersSnapshot,
    RuntimeForexPositionManager,
)
from src.trading.forex_risk import ApprovalStatus, RiskConfiguration, RiskPositionSnapshot, RuntimeForexRiskManager
from src.trading.forex_signals import RuntimeSignalEngine, SignalType
from src.trading.runtime_pipeline.contracts import (
    CandleOutcome,
    PipelineResult,
    PipelineStage,
    RuntimeEvent,
    candle_identity,
)
from src.trading.runtime_pipeline.event_log import RuntimeEventLog


class RuntimeInputs(Protocol):
    """Read/forward seam implemented by the existing broker runtime."""

    def decision_inputs(self, market_snapshot: object): ...  # type: ignore[no-untyped-def]
    def risk_inputs(self, market_snapshot: object): ...  # type: ignore[no-untyped-def]
    def current_position(self, market_snapshot: object) -> RiskPositionSnapshot | None: ...
    def execution_profile(self, market_snapshot: object) -> MT5TradingProfile: ...
    def forward_execution(self, result: ExecutionResult) -> None: ...
    def position_evidence(
        self, market_snapshot: object
    ) -> tuple[MT5PositionSnapshot, PendingOrdersSnapshot, DealHistorySnapshot]: ...
    def update_position_state(self, market_snapshot: object): ...  # type: ignore[no-untyped-def]


class RuntimeMarketData(Protocol):
    def subscribe(self, callback: Callable[[object], PipelineResult]) -> object: ...


class RuntimePipelineRunner:
    """Connect existing runtime stages and stop the current candle on any failure."""

    def __init__(
        self,
        *,
        market_data: RuntimeMarketData,
        feature_builder: RuntimeFeatureBuilder,
        signal_engine: RuntimeSignalEngine,
        decision_engine: RuntimeDecisionEngine,
        risk_manager: RuntimeForexRiskManager,
        executor: RuntimeMT5OrderExecutor,
        position_manager: RuntimeForexPositionManager,
        runtime_inputs: RuntimeInputs,
        event_log: RuntimeEventLog,
        risk_configuration: RiskConfiguration,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        rejection_logger: Callable[[str], None] | None = None,
    ) -> None:
        self.market_data = market_data
        self.feature_builder = feature_builder
        self.signal_engine = signal_engine
        self.decision_engine = decision_engine
        self.risk_manager = risk_manager
        self.executor = executor
        self.position_manager = position_manager
        self.runtime_inputs = runtime_inputs
        self.event_log = event_log
        self.risk_configuration = risk_configuration
        self._clock = clock
        self._log_rejection = rejection_logger or (lambda message: None)
        self._seen_candles: set[str] = set()

    def subscribe(self) -> object:
        """Subscribe this runner to the existing runtime market-data source."""
        return self.market_data.subscribe(self.process_candle)

    def replay(self, snapshots: Iterable[object]) -> tuple[PipelineResult, ...]:
        return tuple(self.process_candle(snapshot) for snapshot in snapshots)

    def process_candle(self, market_snapshot: object) -> PipelineResult:
        events: list[RuntimeEvent] = []
        candle_id: str | None = None
        stage = PipelineStage.MARKET
        try:
            candle_id = candle_identity(market_snapshot)
            if candle_id in self._seen_candles:
                return PipelineResult(candle_id=candle_id, outcome=CandleOutcome.DUPLICATE)
            # Feature Builder is the existing authoritative validated/closed-bar gate.
            feature = self.feature_builder.build(market_snapshot)
            self._seen_candles.add(candle_id)
            events.append(self._append(PipelineStage.MARKET, candle_id, market_snapshot))
            stage = PipelineStage.FEATURE
            events.append(self._append(stage, candle_id, feature))
            if feature.warmup_status is WarmupStatus.WARMING_UP:
                return PipelineResult(
                    candle_id=candle_id, outcome=CandleOutcome.WARMING_UP,
                    events=tuple(events), feature_snapshot=feature,
                )

            stage = PipelineStage.SIGNAL
            signal = self.signal_engine.generate(feature)
            events.append(self._append(stage, candle_id, signal))
            if signal.signal_type is SignalType.HOLD:
                stage = PipelineStage.POSITION
                position = self.runtime_inputs.update_position_state(market_snapshot)
                events.append(self._append(stage, candle_id, position))
                return PipelineResult(
                    candle_id=candle_id, outcome=CandleOutcome.HOLD, events=tuple(events),
                    feature_snapshot=feature, signal_snapshot=signal, position_snapshot=position,
                )

            stage = PipelineStage.DECISION
            position_state, pending_state, quote, strategy_state = self.runtime_inputs.decision_inputs(market_snapshot)
            decision = self.decision_engine.decide(signal, position_state, pending_state, quote, strategy_state)
            events.append(self._append(stage, candle_id, decision))

            stage = PipelineStage.ORDER_PLAN
            account, risk_quote, specification = self.runtime_inputs.risk_inputs(market_snapshot)
            current_position = (
                self.runtime_inputs.current_position(market_snapshot)
                if decision.action is ACTION.CLOSE_POSITION
                else None
            )
            plan = self.risk_manager.assess(
                decision, account, risk_quote, specification, self.risk_configuration, current_position
            )
            events.append(self._append(stage, candle_id, plan))
            if plan.approval_status is ApprovalStatus.REJECTED:
                self._log_rejection(plan.rejection_reason or "RISK_REJECTED")
                return PipelineResult(
                    candle_id=candle_id, outcome=CandleOutcome.RISK_REJECTED, events=tuple(events),
                    feature_snapshot=feature, signal_snapshot=signal,
                    decision_snapshot=decision, order_plan=plan,
                )

            stage = PipelineStage.EXECUTION
            position_ticket = current_position.position_ticket if current_position is not None else None
            position_side = current_position.direction.value if current_position is not None else None
            execution = self.executor.execute(
                plan, specification, risk_quote, self.runtime_inputs.execution_profile(market_snapshot),
                position_ticket, position_side,
            )
            events.append(self._append(stage, candle_id, execution))

            stage = PipelineStage.POSITION
            self.runtime_inputs.forward_execution(execution)
            positions, pending_orders, deals = self.runtime_inputs.position_evidence(market_snapshot)
            position = self.position_manager.reconcile(plan, positions, pending_orders, deals)
            events.append(self._append(stage, candle_id, position))
            return PipelineResult(
                candle_id=candle_id, outcome=CandleOutcome.COMPLETED, events=tuple(events),
                feature_snapshot=feature, signal_snapshot=signal, decision_snapshot=decision,
                order_plan=plan, execution_result=execution, position_snapshot=position,
            )
        except DuplicateBarError:
            return PipelineResult(candle_id=candle_id, outcome=CandleOutcome.DUPLICATE, events=tuple(events))
        except Exception as exc:
            # A failure record is audit evidence only; no business stage follows it.
            if candle_id is not None:
                events.append(self._append(PipelineStage.FAILURE, candle_id, {
                    "failed_stage": stage.value, "error_type": type(exc).__name__, "message": str(exc)
                }))
            return PipelineResult(
                candle_id=candle_id, outcome=CandleOutcome.FAILED, events=tuple(events),
                error_stage=stage, error_message=str(exc),
            )

    def _append(self, stage: PipelineStage, candle_id: str, payload: object) -> RuntimeEvent:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("pipeline clock must return a timezone-aware datetime")
        return self.event_log.append(stage, candle_id, now.astimezone(timezone.utc), payload)
