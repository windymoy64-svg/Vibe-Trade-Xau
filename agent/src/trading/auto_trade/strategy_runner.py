"""Adaptive closed-candle strategy orchestration for the MT5 demo runner.

Every decision evaluates the complete installed selection and precision stack.
The selector chooses the market-appropriate strategy first; precision evidence
then decides whether that strategy has a safe executable entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.trading.auto_selection import (
    MarketIndicatorSnapshot,
    OHLCVBar,
    RealtimeMarketIndicatorService,
    StrategySelectionResult,
    StrategySelectionService,
)
from src.trading.auto_trade.signal_validator import (
    DiagnosticSignalValidationService,
    SignalValidationContext,
)
from src.trading.precision_execution import (
    ACRZone,
    ACRZoneDetectionService,
    ACRZoneStatusValidationService,
    DynamicEntryAreaSelector,
    EntryAreaCandidate,
    EntryOrderTypeService,
    FairValueGapDetectionService,
    FibonacciPremiumDiscountService,
    HTFMarketStructureService,
    LTFSupplyDemandService,
    LotSizeCalculationService,
    OrderBlock,
    OrderBlockDetectionService,
    RACRReversalDetectionService,
    SupportResistanceDetectionService,
    TradeLevelCalculationService,
    evaluate_setup,
)

Direction = Literal["BUY", "SELL"]


@dataclass(frozen=True, slots=True)
class ExecutionMarketData:
    """Broker metadata needed for conservative risk-based sizing."""

    balance: float
    tick_size: float
    tick_value_per_lot: float
    minimum_lot: float
    maximum_lot: float
    lot_step: float
    pip_size: float


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    """Explainable result of one complete market evaluation."""

    snapshot: MarketIndicatorSnapshot
    selection: StrategySelectionResult
    executable: bool
    direction: Direction | None
    strategy_id: str | None
    order_type: str | None
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    lot_size: float | None
    acr_zones: tuple[ACRZone, ...]
    order_blocks: tuple[OrderBlock, ...]
    selected_entry_area: EntryAreaCandidate | None
    entry_area_candidates: tuple[EntryAreaCandidate, ...]
    reason: str


class AdaptiveStrategyRunner:
    """Run all installed strategy and precision indicators on finalized bars."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        *,
        signal_validator: DiagnosticSignalValidationService | None = None,
        max_retest_candles: int = 24,
        max_zone_touches: int = 2,
    ) -> None:
        self._symbol = symbol.strip().upper()
        self._timeframe = timeframe.strip().upper()
        self._signal_validator = signal_validator
        self._selector = StrategySelectionService()
        self._structure = HTFMarketStructureService()
        self._supply_demand = LTFSupplyDemandService()
        self._acr = ACRZoneDetectionService()
        self._acr_status = ACRZoneStatusValidationService()
        self._order_blocks = OrderBlockDetectionService()
        self._support_resistance = SupportResistanceDetectionService()
        self._entry_area_selector = DynamicEntryAreaSelector()
        self._racr = RACRReversalDetectionService()
        self._fvg = FairValueGapDetectionService()
        self._fibonacci = FibonacciPremiumDiscountService()
        self._order_type = EntryOrderTypeService()
        self._levels = TradeLevelCalculationService()
        self._lot_size = LotSizeCalculationService()
        if max_retest_candles <= 0 or max_zone_touches <= 0:
            raise ValueError("setup lifecycle limits must be positive")
        self._max_retest_candles = max_retest_candles
        self._max_zone_touches = max_zone_touches

    def evaluate(
        self,
        bars: tuple[OHLCVBar, ...] | list[OHLCVBar],
        *,
        spread_pips: float,
        session: str,
        market: ExecutionMarketData,
        user_id: str = "default",
        risk_percentage: float = 1.0,
    ) -> StrategyDecision:
        """Evaluate every component and return an order only when all gates pass."""
        ordered = tuple(bars)
        if len(ordered) < 21:
            raise ValueError("at least 21 closed candles are required")
        indicators = RealtimeMarketIndicatorService(self._symbol, self._timeframe)
        snapshot = indicators.extend(ordered)
        selection = self._selector.select(snapshot, session=session, spread_pips=spread_pips)
        if selection.selected_strategy_id is None:
            return self._blocked(snapshot, selection, (), (), None, (), selection.reason)

        structure = self._structure.map(ordered)
        order_blocks = tuple(
            self._order_blocks.validate(block, ordered)
            for block in self._order_blocks.detect(ordered, structure)
        )
        supply_demand = self._supply_demand.detect(ordered)
        acr_zones = tuple(self._acr_status.validate(zone, ordered) for zone in self._acr.detect(ordered))
        gaps = self._fvg.detect(ordered)
        support_resistance = self._support_resistance.detect(ordered, structure)
        reversals = self._racr.detect(ordered)
        direction = self._direction(selection.selected_strategy_id, snapshot.rsi, snapshot.trend)
        expected_bias = "BULLISH" if direction == "BUY" else "BEARISH"

        if selection.selected_strategy_id != "range-mean-reversion" and structure.bias != expected_bias:
            return self._blocked(snapshot, selection, acr_zones, order_blocks, None, (), "HTF market structure does not confirm the selected direction.")
        if (
            selection.selected_strategy_id == "range-mean-reversion"
            and _has_fresh_structure_break(structure, len(ordered))
        ):
            return self._blocked(snapshot, selection, acr_zones, order_blocks, None, (), "Range strategy requires neutral HTF market structure.")

        candidates = self._entry_area_selector.select(
            current_price=snapshot.close,
            direction=expected_bias,
            order_blocks=order_blocks,
            acr_zones=acr_zones,
            gaps=gaps,
            supply_demand=supply_demand,
            support_resistance=support_resistance,
            bars=ordered,
        )
        if not candidates:
            return self._blocked(snapshot, selection, acr_zones, order_blocks, None, (), "No valid entry area supports the selected direction.")
        selected_area = candidates[0]
        selected_acr = next((zone for zone in acr_zones if zone.id == selected_area.id), None)
        if selected_acr is not None:
            setup = evaluate_setup(
                selected_acr, ordered,
                max_retest_candles=self._max_retest_candles,
                max_zone_touches=self._max_zone_touches,
            )
            if setup.state in {"INVALIDATED", "EXPIRED", "TOO_MANY_TOUCHES"}:
                return self._blocked(snapshot, selection, acr_zones, order_blocks, selected_area, candidates, setup.reason)
            rebound_confirmed = setup.state == "REBOUND_CONFIRMED"
        else:
            rebound_confirmed = False

        swing_low = min(bar.low for bar in ordered)
        swing_high = max(bar.high for bar in ordered)
        entry_price = round((selected_area.low + selected_area.high) / 2, 8)
        valuation = self._fibonacci.calculate(
            swing_low=swing_low,
            swing_high=swing_high,
            current_price=snapshot.close,
            setup_zone_midpoint=entry_price,
            setup_direction=direction,
        )
        reversal_confirmed = any(
            reversal.direction == expected_bias and reversal.timestamp == ordered[-1].timestamp.isoformat()
            for reversal in reversals
        )
        rebound_confirmed = rebound_confirmed and (reversal_confirmed or selected_acr is not None)
        order = EntryOrderTypeService(market_tolerance_points=market.pip_size * 0.5).recommend(
            direction=direction,
            current_price=snapshot.close,
            entry_price=entry_price,
            zone_fresh=True,
            valuation_eligible=valuation.eligible,
            has_confluence=selected_area.confluence_count > 0 or selected_area.type in {"ORDER_BLOCK", "ACR", "FVG", "DEMAND", "SUPPLY", "SUPPORT", "RESISTANCE"},
            reversal_confirmed=rebound_confirmed,
        )
        if order.recommendation.startswith("WAIT"):
            return self._blocked(snapshot, selection, acr_zones, order_blocks, selected_area, candidates, " ".join(order.reasons))

        if self._signal_validator is not None:
            validation = self._signal_validator.validate(SignalValidationContext(
                user_id=user_id,
                direction=direction,
                trend=snapshot.trend,
                market_regime=snapshot.regime,
                session=session,
                rsi=snapshot.rsi,
            ))
            if not validation.accepted:
                return self._blocked(snapshot, selection, acr_zones, order_blocks, selected_area, candidates, " ".join(validation.reasons))

        liquidity_candidates = [
            swing.price for swing in structure.swings
            if (direction == "BUY" and swing.kind == "HIGH" and swing.price > entry_price)
            or (direction == "SELL" and swing.kind == "LOW" and swing.price < entry_price)
        ]
        liquidity_target = (min(liquidity_candidates) if direction == "BUY" else max(liquidity_candidates)) if liquidity_candidates else None
        levels = self._levels.calculate(
            direction=direction,
            entry_price=entry_price,
            zone_low=selected_area.low,
            zone_high=selected_area.high,
            pip_size=market.pip_size,
            liquidity_target=liquidity_target,
        )
        sizing = self._lot_size.calculate(
            balance=market.balance,
            risk_percentage=risk_percentage,
            entry_price=levels.entry_price,
            stop_loss=levels.stop_loss,
            tick_size=market.tick_size,
            tick_value_per_lot=market.tick_value_per_lot,
            minimum_lot=market.minimum_lot,
            maximum_lot=market.maximum_lot,
            lot_step=market.lot_step,
        )
        return StrategyDecision(
            snapshot=snapshot,
            selection=selection,
            executable=True,
            direction=direction,
            strategy_id=selection.selected_strategy_id,
            order_type=order.recommendation,
            entry_price=levels.entry_price,
            stop_loss=levels.stop_loss,
            take_profit=levels.targets[-1].price,
            lot_size=sizing.lot_size,
            acr_zones=acr_zones,
            order_blocks=order_blocks,
            selected_entry_area=selected_area,
            entry_area_candidates=candidates,
            reason=" ".join(order.reasons),
        )

    @staticmethod
    def _direction(strategy_id: str, rsi: float | None, trend: str) -> Direction:
        if strategy_id == "range-mean-reversion":
            return "BUY" if (rsi or 50.0) <= 50.0 else "SELL"
        return "BUY" if trend == "BULLISH" else "SELL"


    @staticmethod
    def _blocked(
        snapshot: MarketIndicatorSnapshot,
        selection: StrategySelectionResult,
        acr_zones: tuple[ACRZone, ...],
        order_blocks: tuple[OrderBlock, ...],
        selected_entry_area: EntryAreaCandidate | None,
        entry_area_candidates: tuple[EntryAreaCandidate, ...],
        reason: str,
    ) -> StrategyDecision:
        return StrategyDecision(
            snapshot=snapshot,
            selection=selection,
            executable=False,
            direction=None,
            strategy_id=selection.selected_strategy_id,
            order_type=None,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            lot_size=None,
            acr_zones=acr_zones,
            order_blocks=order_blocks,
            selected_entry_area=selected_entry_area,
            entry_area_candidates=entry_area_candidates,
            reason=reason,
        )


def _has_fresh_structure_break(structure: object, bar_count: int, *, lookback: int = 8) -> bool:
    """Treat only a recent BOS/CHOCH as a range-strategy direction blocker."""
    breaks = getattr(structure, "breaks", ())
    if bar_count <= 0 or lookback <= 0 or not breaks:
        return False
    return (bar_count - 1) - int(breaks[-1].index) <= lookback
