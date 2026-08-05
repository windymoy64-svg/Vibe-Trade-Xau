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
    EntryOrderTypeService,
    FairValueGapDetectionService,
    FibonacciPremiumDiscountService,
    FVGACRConfluenceService,
    HTFMarketStructureService,
    LTFSupplyDemandService,
    LotSizeCalculationService,
    RACRReversalDetectionService,
    TradeLevelCalculationService,
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
    reason: str


class AdaptiveStrategyRunner:
    """Run all installed strategy and precision indicators on finalized bars."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        *,
        signal_validator: DiagnosticSignalValidationService | None = None,
    ) -> None:
        self._symbol = symbol.strip().upper()
        self._timeframe = timeframe.strip().upper()
        self._signal_validator = signal_validator
        self._selector = StrategySelectionService()
        self._structure = HTFMarketStructureService()
        self._supply_demand = LTFSupplyDemandService()
        self._acr = ACRZoneDetectionService()
        self._acr_status = ACRZoneStatusValidationService()
        self._racr = RACRReversalDetectionService()
        self._fvg = FairValueGapDetectionService()
        self._confluence = FVGACRConfluenceService()
        self._fibonacci = FibonacciPremiumDiscountService()
        self._order_type = EntryOrderTypeService()
        self._levels = TradeLevelCalculationService()
        self._lot_size = LotSizeCalculationService()

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
            return self._blocked(snapshot, selection, (), selection.reason)

        structure = self._structure.map(ordered)
        supply_demand = self._supply_demand.detect(ordered)
        acr_zones = tuple(self._acr_status.validate(zone, ordered) for zone in self._acr.detect(ordered))
        gaps = self._fvg.detect(ordered)
        confluences = self._confluence.detect(gaps, acr_zones)
        reversals = self._racr.detect(ordered)
        direction = self._direction(selection.selected_strategy_id, snapshot.rsi, snapshot.trend)
        expected_bias = "BULLISH" if direction == "BUY" else "BEARISH"

        if selection.selected_strategy_id != "range-mean-reversion" and structure.bias != expected_bias:
            return self._blocked(snapshot, selection, acr_zones, "HTF market structure does not confirm the selected direction.")
        if selection.selected_strategy_id == "range-mean-reversion" and structure.bias != "NEUTRAL":
            return self._blocked(snapshot, selection, acr_zones, "Range strategy requires neutral HTF market structure.")

        matching_zones = [zone for zone in acr_zones if zone.status == "FRESH" and zone.direction == expected_bias]
        if not matching_zones:
            return self._blocked(snapshot, selection, acr_zones, "No fresh ACR zone supports the selected strategy.")
        zone = min(matching_zones, key=lambda item: abs(snapshot.close - ((item.low + item.high) / 2)))

        expected_supply_demand = "DEMAND" if direction == "BUY" else "SUPPLY"
        if not any(zone_item.type == expected_supply_demand and zone_item.status != "INVALID" for zone_item in supply_demand):
            return self._blocked(snapshot, selection, acr_zones, "No active supply/demand zone confirms the selected direction.")
        confluence = next((item for item in confluences if item.acr_zone_id == zone.id), None)
        if confluence is None:
            return self._blocked(snapshot, selection, acr_zones, "No active FVG and ACR confluence supports the selected zone.")

        swing_low = min(bar.low for bar in ordered)
        swing_high = max(bar.high for bar in ordered)
        entry_price = round((confluence.overlap_low + confluence.overlap_high) / 2, 8)
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
        order = EntryOrderTypeService(market_tolerance_points=market.pip_size * 0.5).recommend(
            direction=direction,
            current_price=snapshot.close,
            entry_price=entry_price,
            zone_fresh=True,
            valuation_eligible=valuation.eligible,
            has_confluence=True,
            reversal_confirmed=reversal_confirmed,
        )
        if order.recommendation.startswith("WAIT"):
            return self._blocked(snapshot, selection, acr_zones, " ".join(order.reasons))

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
                return self._blocked(snapshot, selection, acr_zones, " ".join(validation.reasons))

        levels = self._levels.calculate(
            direction=direction,
            entry_price=entry_price,
            zone_low=zone.low,
            zone_high=zone.high,
            pip_size=market.pip_size,
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
            reason=reason,
        )
