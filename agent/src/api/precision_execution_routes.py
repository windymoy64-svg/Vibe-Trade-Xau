"""Upload and analyze bounded OHLCV datasets for precision execution."""

from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.api.security import require_local_or_auth
from src.trading.auto_selection import OHLCVBar
from src.trading.precision_execution import (
    ACRZoneDetectionService,
    ACRZoneStatusValidationService,
    EntryOrderRecommendation,
    EntryOrderTypeService,
    FairValueGapDetectionService,
    FibonacciPremiumDiscountService,
    FVGACRConfluenceService,
    HTFMarketStructureService,
    LTFSupplyDemandService,
    LotSizeCalculationService,
    OHLCVFileParser,
    OHLCVParseError,
    RACRReversalDetectionService,
    TradeLevelCalculationService,
)


@dataclass(frozen=True, slots=True)
class PrecisionDataset:
    id: str
    user_id: str
    symbol: str
    timeframe: str
    bars: tuple[OHLCVBar, ...]


class PrecisionDatasetStore:
    def __init__(self, *, maximum_datasets: int = 20) -> None:
        self.maximum_datasets = maximum_datasets
        self._datasets: dict[tuple[str, str], PrecisionDataset] = {}
        self._order: list[tuple[str, str]] = []
        self._lock = threading.RLock()

    def add(
        self, user_id: str, symbol: str, timeframe: str, bars: tuple[OHLCVBar, ...],
    ) -> PrecisionDataset:
        dataset = PrecisionDataset(
            str(uuid.uuid4()), user_id.strip(), symbol.strip().upper(),
            timeframe.strip().upper(), bars,
        )
        key = (dataset.user_id, dataset.id)
        with self._lock:
            self._datasets[key] = dataset
            self._order.append(key)
            while len(self._order) > self.maximum_datasets:
                self._datasets.pop(self._order.pop(0), None)
        return dataset

    def get(self, user_id: str, dataset_id: str) -> PrecisionDataset | None:
        with self._lock:
            return self._datasets.get((user_id.strip(), dataset_id.strip()))

    def clear(self) -> None:
        with self._lock:
            self._datasets.clear()
            self._order.clear()


class OHLCVUploadResponse(BaseModel):
    datasetId: str
    symbol: str
    timeframe: str
    rowCount: int
    startAt: str
    endAt: str


class PrecisionAnalysisRequest(BaseModel):
    userId: str = Field(..., min_length=1, max_length=128)
    datasetId: str = Field(..., min_length=1)
    pipSize: float = Field(..., gt=0)


class PrecisionAnalysisResponse(BaseModel):
    dataset: OHLCVUploadResponse
    currentPrice: float
    bias: str
    generatedAt: str
    marketStructure: dict[str, Any]
    supplyDemandZones: list[dict[str, Any]]
    acrZones: list[dict[str, Any]]
    reversalSignals: list[dict[str, Any]]
    fairValueGaps: list[dict[str, Any]]
    confluences: list[dict[str, Any]]
    fibonacci: dict[str, Any] | None
    orderRecommendation: dict[str, Any]
    tradeLevels: dict[str, Any] | None


class RiskCalculatorRequest(BaseModel):
    balance: float = Field(..., ge=100, allow_inf_nan=False)
    riskPercentage: float = Field(..., gt=0, le=5, allow_inf_nan=False)
    entryPrice: float = Field(..., gt=0, allow_inf_nan=False)
    stopLoss: float = Field(..., gt=0, allow_inf_nan=False)
    tickSize: float = Field(0.1, gt=0, allow_inf_nan=False)
    tickValuePerLot: float = Field(10.0, gt=0, allow_inf_nan=False)
    minimumLot: float = Field(0.01, gt=0, allow_inf_nan=False)
    maximumLot: float = Field(1.0, gt=0, allow_inf_nan=False)
    lotStep: float = Field(0.01, gt=0, allow_inf_nan=False)


class RiskCalculatorResponse(BaseModel):
    balance: float
    riskPercentage: float
    riskAmount: float
    stopDistance: float
    lotSize: float
    actualRiskAmount: float
    boundedBy: str | None


precision_dataset_store = PrecisionDatasetStore()


def register_precision_execution_routes(app: Any) -> None:
    @app.post(
        "/precision-execution/risk-calculator",
        response_model=RiskCalculatorResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def calculate_precision_risk(
        request: RiskCalculatorRequest,
    ) -> RiskCalculatorResponse:
        try:
            result = LotSizeCalculationService().calculate(
                balance=request.balance,
                risk_percentage=request.riskPercentage,
                entry_price=request.entryPrice,
                stop_loss=request.stopLoss,
                tick_size=request.tickSize,
                tick_value_per_lot=request.tickValuePerLot,
                minimum_lot=request.minimumLot,
                maximum_lot=request.maximumLot,
                lot_step=request.lotStep,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return RiskCalculatorResponse(
            balance=result.balance,
            riskPercentage=result.risk_percentage,
            riskAmount=result.risk_amount,
            stopDistance=result.stop_distance,
            lotSize=result.lot_size,
            actualRiskAmount=result.actual_risk_amount,
            boundedBy=result.bounded_by,
        )

    @app.post(
        "/precision-execution/ohlcv",
        response_model=OHLCVUploadResponse,
        status_code=201,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def upload_ohlcv(
        file: UploadFile = File(...),
        user_id: str = Form("default", alias="userId", min_length=1, max_length=128),
        symbol: str = Form(..., min_length=2, max_length=32),
        timeframe: str = Form(..., min_length=1, max_length=16),
    ) -> OHLCVUploadResponse:
        parser = OHLCVFileParser()
        content = await file.read(parser.maximum_bytes + 1)
        await file.close()
        try:
            bars = parser.parse(file.filename or "", content)
        except OHLCVParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        dataset = precision_dataset_store.add(user_id, symbol, timeframe, bars)
        return OHLCVUploadResponse(
            datasetId=dataset.id,
            symbol=dataset.symbol,
            timeframe=dataset.timeframe,
            rowCount=len(dataset.bars),
            startAt=dataset.bars[0].timestamp.isoformat(),
            endAt=dataset.bars[-1].timestamp.isoformat(),
        )

    @app.post(
        "/precision-execution/analyze",
        response_model=PrecisionAnalysisResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def analyze_precision_execution(
        request: PrecisionAnalysisRequest,
    ) -> PrecisionAnalysisResponse:
        dataset = precision_dataset_store.get(request.userId, request.datasetId)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Precision dataset not found")

        bars = dataset.bars
        try:
            market_structure = HTFMarketStructureService().map(bars)
            supply_demand_zones = LTFSupplyDemandService().detect(bars)
            detected_acr_zones = ACRZoneDetectionService().detect(bars)
            status_service = ACRZoneStatusValidationService()
            acr_zones = tuple(status_service.validate(zone, bars) for zone in detected_acr_zones)
            reversal_signals = RACRReversalDetectionService().detect(bars)
            fair_value_gaps = FairValueGapDetectionService().detect(bars)
            confluences = FVGACRConfluenceService().detect(fair_value_gaps, acr_zones)

            selected_zone = next((
                zone for zone in reversed(acr_zones)
                if zone.status == "FRESH" and zone.direction == market_structure.bias
            ), None)
            current_price = bars[-1].close
            fibonacci = None
            trade_levels = None

            if market_structure.bias == "NEUTRAL" or selected_zone is None:
                reason = (
                    "HTF market structure is neutral."
                    if market_structure.bias == "NEUTRAL"
                    else "No fresh ACR zone matches the HTF bias."
                )
                order_recommendation = EntryOrderRecommendation(
                    "WAIT", "BLOCKED", current_price, current_price, 0.0, (reason,),
                )
            else:
                direction = "BUY" if selected_zone.direction == "BULLISH" else "SELL"
                zone_midpoint = (selected_zone.low + selected_zone.high) / 2
                fibonacci = FibonacciPremiumDiscountService().calculate(
                    swing_low=min(bar.low for bar in bars),
                    swing_high=max(bar.high for bar in bars),
                    current_price=current_price,
                    setup_zone_midpoint=zone_midpoint,
                    setup_direction=direction,
                )
                order_recommendation = EntryOrderTypeService().recommend(
                    direction=direction,
                    current_price=current_price,
                    entry_price=zone_midpoint,
                    zone_fresh=True,
                    valuation_eligible=fibonacci.eligible,
                    has_confluence=any(
                        item.direction == selected_zone.direction
                        and item.acr_zone_id == selected_zone.id
                        for item in confluences
                    ),
                    reversal_confirmed=any(
                        signal.direction == selected_zone.direction
                        for signal in reversal_signals
                    ),
                )
                if order_recommendation.recommendation != "WAIT":
                    trade_levels = TradeLevelCalculationService().calculate(
                        direction=direction,
                        entry_price=zone_midpoint,
                        zone_low=selected_zone.low,
                        zone_high=selected_zone.high,
                        pip_size=request.pipSize,
                    )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return PrecisionAnalysisResponse(
            dataset=OHLCVUploadResponse(
                datasetId=dataset.id,
                symbol=dataset.symbol,
                timeframe=dataset.timeframe,
                rowCount=len(bars),
                startAt=bars[0].timestamp.isoformat(),
                endAt=bars[-1].timestamp.isoformat(),
            ),
            currentPrice=current_price,
            bias=market_structure.bias,
            generatedAt=datetime.now(timezone.utc).isoformat(),
            marketStructure=asdict(market_structure),
            supplyDemandZones=[asdict(zone) for zone in supply_demand_zones],
            acrZones=[asdict(zone) for zone in acr_zones],
            reversalSignals=[asdict(signal) for signal in reversal_signals],
            fairValueGaps=[asdict(gap) for gap in fair_value_gaps],
            confluences=[asdict(confluence) for confluence in confluences],
            fibonacci=asdict(fibonacci) if fibonacci is not None else None,
            orderRecommendation=asdict(order_recommendation),
            tradeLevels=asdict(trade_levels) if trade_levels is not None else None,
        )
