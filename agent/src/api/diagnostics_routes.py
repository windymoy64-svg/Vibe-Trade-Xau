"""REST endpoints for production trade diagnostics."""

from __future__ import annotations

import csv
import html
import io
from datetime import datetime
from typing import Any, Literal

from fastapi import Depends, File, Form, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.api.security import require_local_or_auth
from src.diagnostics.store import DiagnosticsStore
from src.diagnostics.recommendation_service import DiagnosticRecommendationService


class DiagnosticsSummaryResponse(BaseModel):
    totalTrades: int
    winningTrades: int
    losingTrades: int
    lossRate: float


class DiagnosticCauseResponse(BaseModel):
    label: str
    count: int
    percentage: float


class RecentDiagnosticTradeResponse(BaseModel):
    id: str
    ticketId: str
    pair: str
    direction: str
    result: str
    suspectedReason: str | None
    profitLoss: float | None
    entryTime: str


class DiagnosticsInsightResponse(BaseModel):
    cause: str
    percentage: float
    recommendation: str


class LossPatternResponse(BaseModel):
    id: str
    name: str
    category: Literal["TREND", "REGIME", "SESSION", "MOMENTUM"]
    description: str
    lossCount: int
    lossPercentage: float
    confidence: float
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    evidenceTradeIds: list[str]
    trendDelta: float


class LossPatternSummaryResponse(BaseModel):
    totalLosses: int
    classifiedLosses: int
    lossesClassifiedPct: float


class LossPatternInsightResponse(BaseModel):
    title: str
    detail: str


class LossPatternAnalysisResponse(BaseModel):
    summary: LossPatternSummaryResponse
    patterns: list[LossPatternResponse]
    insight: LossPatternInsightResponse
    generatedAt: str


class LossPatternPeriodResponse(BaseModel):
    start: str
    end: str


class LossPatternComparisonSummaryResponse(BaseModel):
    improving: int
    worsening: int
    stable: int


class LossPatternComparisonItemResponse(BaseModel):
    id: str
    name: str
    category: Literal["TREND", "REGIME", "SESSION", "MOMENTUM"]
    description: str
    currentLossCount: int
    currentShare: float
    baselineLossCount: int
    baselineShare: float
    deltaPercentagePoints: float
    status: Literal["improving", "worsening", "stable"]
    confidence: float
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    evidenceTradeIds: list[str]


class LossPatternComparisonResponse(BaseModel):
    currentPeriod: LossPatternPeriodResponse
    baselinePeriod: LossPatternPeriodResponse
    summary: LossPatternComparisonSummaryResponse
    patterns: list[LossPatternComparisonItemResponse]


class DiagnosticRecommendationResponse(BaseModel):
    id: str
    title: str
    summary: str
    action: str
    patternId: str
    patternName: str
    priority: Literal["CRITICAL", "HIGH", "MEDIUM"]
    status: Literal["READY", "REVIEW", "APPLIED"]
    expectedImpact: float
    evidenceLosses: int
    confidence: float
    effort: Literal["LOW", "MEDIUM", "HIGH"]
    steps: list[str]
    validationTarget: str
    guardrail: str


class DiagnosticRecommendationsResponse(BaseModel):
    recommendations: list[DiagnosticRecommendationResponse]
    generatedAt: str


class ImprovementTimelineResponse(BaseModel):
    id: str
    recommendationId: str
    title: str
    description: str
    status: Literal["PLANNED", "APPLIED", "MONITORING", "VALIDATED"]
    occurredAt: str
    owner: str
    evidenceNote: str | None


class LossReductionPointResponse(BaseModel):
    label: str
    lossRate: float
    tradeCount: int


class ImprovementSuccessMetricResponse(BaseModel):
    id: str
    label: str
    current: str
    target: str
    progress: float
    status: Literal["ACHIEVED", "ON_TRACK", "AT_RISK"]
    detail: str


class ImprovementActivityResponse(BaseModel):
    id: str
    type: Literal["NOTE", "STATUS_CHANGE", "EVIDENCE"]
    message: str
    actor: str
    occurredAt: str
    recommendationId: str


class UpdateDiagnosticRecommendationStatusRequest(BaseModel):
    user_id: str = "default"
    status: Literal["READY", "REVIEW", "APPLIED"]


class DiagnosticTradeListResponse(BaseModel):
    items: list[dict[str, object]]
    total: int
    limit: int
    offset: int


class DiagnosticExportRequest(BaseModel):
    trade_ids: list[str]
    format: Literal["csv", "pdf"]
    user_id: str = "default"


class ImprovementReportRequest(BaseModel):
    user_id: str = "default"
    sections: list[Literal["metrics", "timeline", "activity"]] = [
        "metrics", "timeline", "activity",
    ]


class SaveDiagnosticFilterRequest(BaseModel):
    user_id: str = "default"
    name: str
    criteria: dict[str, object]


class ConnectDataSourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=128)
    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    coverage: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("name", "type", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("coverage")
    @classmethod
    def validate_coverage(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if not item or len(item) > 80:
                raise ValueError("coverage items must be 1-80 characters")
            if item not in normalized:
                normalized.append(item)
        return normalized


class DataSourceResponse(BaseModel):
    id: str
    userId: str
    name: str
    type: str
    description: str
    status: Literal["CONNECTED", "AVAILABLE", "ATTENTION"]
    lastSyncAt: str | None
    importedTrades: int
    coverage: list[str]
    createdAt: str
    updatedAt: str


class CsvTradeImportResponse(BaseModel):
    imported: int
    skipped: int
    totalRows: int
    sourceId: str


_CSV_MAX_BYTES = 5 * 1024 * 1024
_CSV_MAX_ROWS = 10_000
_CSV_REQUIRED_COLUMNS = {
    "ticket_id", "pair", "entry_time", "direction", "result", "market_regime",
    "trading_session", "trend_status", "ema_alignment", "rsi_value", "atr_value",
    "volume_status",
}


def _csv_optional_float(row: dict[str, str], key: str, row_number: int) -> float | None:
    raw = (row.get(key) or "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {key} must be numeric") from exc


def _parse_diagnostic_csv(content: bytes) -> list[dict[str, object]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must use UTF-8 encoding") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = {header.strip() for header in (reader.fieldnames or []) if header}
    missing = sorted(_CSV_REQUIRED_COLUMNS - headers)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")
    trades: list[dict[str, object]] = []
    enum_fields = {
        "direction": {"BUY", "SELL"}, "result": {"TP", "SL"},
        "market_regime": {"TRENDING", "RANGING", "BREAKOUT"},
        "trading_session": {"ASIA", "LONDON", "NEW_YORK"},
        "trend_status": {"BULLISH", "BEARISH", "FLAT"},
        "ema_alignment": {"BULLISH", "BEARISH", "MIXED"},
        "volume_status": {"NORMAL", "HIGH", "LOW"},
    }
    for row_number, raw_row in enumerate(reader, start=2):
        if len(trades) >= _CSV_MAX_ROWS:
            raise ValueError(f"CSV exceeds {_CSV_MAX_ROWS} data rows")
        row = {(key or "").strip(): (value or "").strip() for key, value in raw_row.items()}
        if not any(row.values()):
            continue
        for key in _CSV_REQUIRED_COLUMNS:
            if not row.get(key):
                raise ValueError(f"row {row_number}: {key} is required")
        for key, allowed in enum_fields.items():
            row[key] = row[key].upper()
            if row[key] not in allowed:
                raise ValueError(f"row {row_number}: invalid {key}")
        try:
            datetime.fromisoformat(row["entry_time"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"row {row_number}: entry_time must be ISO-8601") from exc
        rsi = _csv_optional_float(row, "rsi_value", row_number)
        atr = _csv_optional_float(row, "atr_value", row_number)
        if rsi is None or not 0 <= rsi <= 100:
            raise ValueError(f"row {row_number}: rsi_value must be between 0 and 100")
        if atr is None or atr < 0:
            raise ValueError(f"row {row_number}: atr_value must be non-negative")
        trades.append({
            "ticket_id": row["ticket_id"], "pair": row["pair"].upper(),
            "entry_time": row["entry_time"], "direction": row["direction"],
            "result": row["result"], "market_regime": row["market_regime"],
            "trading_session": row["trading_session"], "trend_status": row["trend_status"],
            "ema_alignment": row["ema_alignment"], "rsi_value": rsi, "atr_value": atr,
            "volume_status": row["volume_status"],
            "suspected_reason": row.get("suspected_reason") or None,
            "profit_loss": _csv_optional_float(row, "profit_loss", row_number),
            "entry_price": _csv_optional_float(row, "entry_price", row_number),
            "exit_price": _csv_optional_float(row, "exit_price", row_number),
            "exit_time": row.get("exit_time") or None,
        })
    if not trades:
        raise ValueError("CSV contains no trade rows")
    return trades


def register_diagnostics_routes(app: Any) -> None:
    """Register diagnostics read endpoints on the host FastAPI app."""

    @app.get(
        "/diagnostics/summary",
        response_model=DiagnosticsSummaryResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostics_summary(
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> DiagnosticsSummaryResponse:
        with DiagnosticsStore() as store:
            return DiagnosticsSummaryResponse(**store.performance_summary(user_id))

    @app.get(
        "/diagnostics/causes",
        response_model=list[DiagnosticCauseResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_causes(
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> list[DiagnosticCauseResponse]:
        with DiagnosticsStore() as store:
            return [DiagnosticCauseResponse(**item) for item in store.cause_statistics(user_id)]

    @app.get(
        "/diagnostics/trades/recent",
        response_model=list[RecentDiagnosticTradeResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def recent_diagnostic_trades(
        user_id: str = Query("default", min_length=1, max_length=128),
        limit: int = Query(5, ge=1, le=100),
    ) -> list[RecentDiagnosticTradeResponse]:
        with DiagnosticsStore() as store:
            return [RecentDiagnosticTradeResponse(**item) for item in store.recent_trades(user_id, limit)]

    @app.get(
        "/diagnostics/insight",
        response_model=DiagnosticsInsightResponse | None,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostics_insight(
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> DiagnosticsInsightResponse | None:
        with DiagnosticsStore() as store:
            insight = store.quick_insight(user_id)
        return DiagnosticsInsightResponse(**insight) if insight else None

    @app.get(
        "/diagnostics/patterns",
        response_model=LossPatternAnalysisResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_loss_patterns(
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> LossPatternAnalysisResponse:
        with DiagnosticsStore() as store:
            analysis = store.loss_pattern_analysis(user_id)
        return LossPatternAnalysisResponse.model_validate(analysis)

    @app.get(
        "/diagnostics/patterns/compare",
        response_model=LossPatternComparisonResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def compare_diagnostic_loss_patterns(
        current_start: str = Query(..., min_length=1, max_length=40),
        current_end: str = Query(..., min_length=1, max_length=40),
        baseline_start: str = Query(..., min_length=1, max_length=40),
        baseline_end: str = Query(..., min_length=1, max_length=40),
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> LossPatternComparisonResponse:
        if current_start > current_end or baseline_start > baseline_end:
            raise HTTPException(status_code=422, detail="Period start must not be after period end")
        with DiagnosticsStore() as store:
            comparison = store.compare_loss_pattern_periods(
                user_id, current_start, current_end, baseline_start, baseline_end,
            )
        return LossPatternComparisonResponse.model_validate(comparison)

    @app.get(
        "/diagnostics/recommendations",
        response_model=DiagnosticRecommendationsResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_recommendations(
        user_id: str = Query("default", min_length=1, max_length=128),
        priority: Literal["CRITICAL", "HIGH", "MEDIUM"] | None = Query(None),
    ) -> DiagnosticRecommendationsResponse:
        with DiagnosticsStore() as store:
            payload = DiagnosticRecommendationService(store).list_recommendations(
                user_id, priority_filter=priority,
            )
        return DiagnosticRecommendationsResponse.model_validate(payload)

    @app.get(
        "/diagnostics/recommendations/{recommendation_id}",
        response_model=DiagnosticRecommendationResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_recommendation_detail(
        recommendation_id: str,
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> DiagnosticRecommendationResponse:
        if not recommendation_id or len(recommendation_id) > 256:
            raise HTTPException(status_code=422, detail="Invalid recommendation ID")
        with DiagnosticsStore() as store:
            recommendation = DiagnosticRecommendationService(store).get_recommendation(
                user_id, recommendation_id,
            )
        if recommendation is None:
            raise HTTPException(status_code=404, detail="Diagnostic recommendation not found")
        return DiagnosticRecommendationResponse.model_validate(recommendation)

    @app.patch(
        "/diagnostics/recommendations/{recommendation_id}/status",
        response_model=DiagnosticRecommendationResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def update_diagnostic_recommendation_status(
        recommendation_id: str,
        payload: UpdateDiagnosticRecommendationStatusRequest,
    ) -> DiagnosticRecommendationResponse:
        if not recommendation_id or len(recommendation_id) > 256:
            raise HTTPException(status_code=422, detail="Invalid recommendation ID")
        user_id = payload.user_id.strip()
        if not user_id or len(user_id) > 128:
            raise HTTPException(status_code=422, detail="Invalid user ID")
        with DiagnosticsStore() as store:
            recommendation = DiagnosticRecommendationService(store).update_recommendation_status(
                user_id, recommendation_id, payload.status,
            )
        if recommendation is None:
            raise HTTPException(status_code=404, detail="Diagnostic recommendation not found")
        return DiagnosticRecommendationResponse.model_validate(recommendation)

    @app.get(
        "/diagnostics/improvements/timeline",
        response_model=list[ImprovementTimelineResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_improvement_timeline(
        user_id: str = Query("default", min_length=1, max_length=128),
        limit: int = Query(50, ge=1, le=200),
    ) -> list[ImprovementTimelineResponse]:
        with DiagnosticsStore() as store:
            timeline = store.improvement_timeline(user_id, limit=limit)
        return [ImprovementTimelineResponse.model_validate(item) for item in timeline]

    @app.get(
        "/diagnostics/improvements/loss-reduction",
        response_model=list[LossReductionPointResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_improvement_loss_reduction(
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> list[LossReductionPointResponse]:
        with DiagnosticsStore() as store:
            points = store.improvement_loss_reduction(user_id)
        return [LossReductionPointResponse.model_validate(item) for item in points]

    @app.get(
        "/diagnostics/improvements/success-metrics",
        response_model=list[ImprovementSuccessMetricResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_improvement_success_metrics(
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> list[ImprovementSuccessMetricResponse]:
        with DiagnosticsStore() as store:
            metrics = store.improvement_success_metrics(user_id)
        return [ImprovementSuccessMetricResponse.model_validate(item) for item in metrics]

    @app.get(
        "/diagnostics/improvements/activity",
        response_model=list[ImprovementActivityResponse],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_improvement_activity(
        user_id: str = Query("default", min_length=1, max_length=128),
        limit: int = Query(50, ge=1, le=200),
    ) -> list[ImprovementActivityResponse]:
        with DiagnosticsStore() as store:
            activities = store.improvement_activity_log(user_id, limit=limit)
        return [ImprovementActivityResponse.model_validate(item) for item in activities]

    @app.post(
        "/diagnostics/improvements/export/pdf",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def export_diagnostic_improvement_report(
        payload: ImprovementReportRequest,
    ) -> Response:
        user_id = payload.user_id.strip()
        if not user_id or len(user_id) > 128:
            raise HTTPException(status_code=422, detail="Invalid user ID")
        sections = list(dict.fromkeys(payload.sections))
        if not sections:
            raise HTTPException(status_code=422, detail="Select at least one report section")
        with DiagnosticsStore() as store:
            timeline = store.improvement_timeline(user_id, limit=200)
            loss_points = store.improvement_loss_reduction(user_id)
            metrics = store.improvement_success_metrics(user_id)
            activities = store.improvement_activity_log(user_id, limit=200)

        baseline = loss_points[0]["lossRate"] if loss_points else 0
        latest = loss_points[-1]["lossRate"] if loss_points else 0
        metric_rows = "".join(
            f"<tr><td>{html.escape(str(item['label']))}</td><td>{html.escape(str(item['current']))}</td>"
            f"<td>{html.escape(str(item['target']))}</td><td>{html.escape(str(item['status']))}</td></tr>"
            for item in metrics
        ) or '<tr><td colspan="4">No success metrics available.</td></tr>'
        timeline_rows = "".join(
            f"<tr><td>{html.escape(str(item['occurredAt']))}</td><td>{html.escape(str(item['title']))}</td>"
            f"<td>{html.escape(str(item['status']))}</td><td>{html.escape(str(item['owner']))}</td></tr>"
            for item in timeline
        ) or '<tr><td colspan="4">No improvements tracked.</td></tr>'
        activity_rows = "".join(
            f"<li><strong>{html.escape(str(item['actor']))}</strong> — "
            f"{html.escape(str(item['message']))}<small>{html.escape(str(item['occurredAt']))}</small></li>"
            for item in activities
        ) or "<li>No activity recorded.</li>"
        selected = set(sections)
        document = f"""<html><head><style>
            body{{font:13px sans-serif;color:#111;padding:28px}} h1{{margin-bottom:4px}}
            .meta{{color:#666}} .summary{{display:flex;gap:12px;margin:18px 0}}
            .metric{{border:1px solid #ddd;padding:10px;min-width:130px}}
            .metric strong{{display:block;font-size:20px}} table{{width:100%;border-collapse:collapse;margin-bottom:20px}}
            th,td{{border:1px solid #ddd;padding:7px;text-align:left}} th{{background:#eee}}
            li{{margin:7px 0}} small{{display:block;color:#666}}
        </style></head><body><h1>Improvement progress report</h1>
        <p class="meta">User: {html.escape(user_id)}</p>
        <div class="summary"><div class="metric">Baseline loss rate<strong>{baseline}%</strong></div>
        <div class="metric">Latest loss rate<strong>{latest}%</strong></div>
        <div class="metric">Tracked changes<strong>{len(timeline)}</strong></div></div>
        {f'<h2>Success metrics</h2><table><tr><th>Metric</th><th>Current</th><th>Target</th><th>Status</th></tr>{metric_rows}</table>' if 'metrics' in selected else ''}
        {f'<h2>Improvement timeline</h2><table><tr><th>Date</th><th>Change</th><th>Status</th><th>Owner</th></tr>{timeline_rows}</table>' if 'timeline' in selected else ''}
        {f'<h2>Activity log</h2><ul>{activity_rows}</ul>' if 'activity' in selected else ''}
        </body></html>"""
        from weasyprint import HTML
        pdf = HTML(string=document).write_pdf()
        return Response(
            pdf, media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="improvement-progress.pdf"'},
        )

    @app.get(
        "/diagnostics/trades",
        response_model=DiagnosticTradeListResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def list_diagnostic_trades(
        user_id: str = Query("default", min_length=1, max_length=128),
        search: str | None = Query(None, max_length=128),
        pair: str | None = Query(None, max_length=20),
        result: str | None = Query(None, pattern="^(TP|SL)$"),
        from_date: str | None = Query(None, max_length=40),
        to_date: str | None = Query(None, max_length=40),
        market_regime: str | None = Query(None, pattern="^(TRENDING|RANGING|BREAKOUT)$"),
        trading_session: str | None = Query(None, pattern="^(ASIA|LONDON|NEW_YORK)$"),
        ema_alignment: str | None = Query(None, pattern="^(BULLISH|BEARISH|MIXED)$"),
        min_rsi: float | None = Query(None, ge=0, le=100),
        max_rsi: float | None = Query(None, ge=0, le=100),
        min_atr: float | None = Query(None, ge=0),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> DiagnosticTradeListResponse:
        with DiagnosticsStore() as store:
            payload = store.list_trades(
                user_id, search=search, pair=pair, result=result,
                from_date=from_date, to_date=to_date, market_regime=market_regime,
                trading_session=trading_session, ema_alignment=ema_alignment,
                min_rsi=min_rsi, max_rsi=max_rsi, min_atr=min_atr,
                limit=limit, offset=offset,
            )
        return DiagnosticTradeListResponse(**payload)

    @app.get(
        "/diagnostics/trades/{trade_id}",
        response_model=dict[str, object],
        dependencies=[Depends(require_local_or_auth)],
    )
    async def diagnostic_trade_detail(
        trade_id: str,
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> dict[str, object]:
        with DiagnosticsStore() as store:
            trade = store.get_trade(user_id, trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail="Diagnostic trade not found")
        return trade

    @app.post(
        "/diagnostics/trades/export",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def export_diagnostic_trades(payload: DiagnosticExportRequest) -> Response:
        if not payload.trade_ids or len(payload.trade_ids) > 100:
            raise HTTPException(status_code=422, detail="Select between 1 and 100 trades")
        with DiagnosticsStore() as store:
            trades = store.get_trades_by_ids(payload.user_id, payload.trade_ids)
        if not trades:
            raise HTTPException(status_code=404, detail="No selected diagnostic trades found")
        if payload.format == "csv":
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, fieldnames=list(trades[0].keys()), extrasaction="ignore")
            writer.writeheader()
            writer.writerows(trades)
            return Response(
                output.getvalue(), media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="trade-diagnostics.csv"'},
            )
        rows = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(trade.get(key) or '—'))}</td>" for key in ("ticket_id", "entry_time", "direction", "result", "market_regime", "suspected_reason", "profit_loss")) + "</tr>"
            for trade in trades
        )
        document = f"""<html><head><style>body{{font:12px sans-serif}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #ccc;padding:6px;text-align:left}}th{{background:#eee}}</style></head><body><h1>Trade diagnostic report</h1><table><thead><tr><th>Ticket</th><th>Entry</th><th>Direction</th><th>Result</th><th>Regime</th><th>Diagnosis</th><th>P/L</th></tr></thead><tbody>{rows}</tbody></table></body></html>"""
        from weasyprint import HTML
        pdf = HTML(string=document).write_pdf()
        return Response(
            pdf, media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="trade-diagnostics.pdf"'},
        )

    @app.post(
        "/diagnostics/filters",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def save_diagnostic_filter(payload: SaveDiagnosticFilterRequest) -> dict[str, object]:
        name = payload.name.strip()
        if not name or len(name) > 80:
            raise HTTPException(status_code=422, detail="Filter name must be 1-80 characters")
        with DiagnosticsStore() as store:
            return store.save_filter_preset(payload.user_id, name, payload.criteria)

    @app.get(
        "/diagnostics/filters",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def list_diagnostic_filters(
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> list[dict[str, object]]:
        with DiagnosticsStore() as store:
            return store.list_filter_presets(user_id)

    @app.delete(
        "/diagnostics/filters/{preset_id}",
        dependencies=[Depends(require_local_or_auth)],
    )
    async def delete_diagnostic_filter(
        preset_id: str,
        user_id: str = Query("default", min_length=1, max_length=128),
    ) -> dict[str, bool]:
        with DiagnosticsStore() as store:
            deleted = store.delete_filter_preset(user_id, preset_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Diagnostic filter not found")
        return {"deleted": True}

    @app.post(
        "/data-sources/connect",
        response_model=DataSourceResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def connect_data_source(payload: ConnectDataSourceRequest) -> DataSourceResponse:
        """Register connected trading-platform metadata without accepting secrets."""
        with DiagnosticsStore() as store:
            source = store.connect_data_source(
                user_id=payload.user_id,
                source_id=payload.id,
                name=payload.name,
                source_type=payload.type,
                description=payload.description,
                coverage=payload.coverage,
            )
        if source is None:
            raise HTTPException(status_code=404, detail="User not found")
        return DataSourceResponse(**source)

    @app.post(
        "/data-sources/csv",
        response_model=CsvTradeImportResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def import_diagnostic_csv(
        user_id: str = Form(..., min_length=1, max_length=128),
        file: UploadFile = File(...),
    ) -> CsvTradeImportResponse:
        """Validate and atomically import a bounded UTF-8 diagnostics CSV."""
        filename = file.filename or ""
        if not filename or not filename.lower().endswith(".csv"):
            await file.close()
            raise HTTPException(status_code=400, detail="A .csv file is required")
        content = bytearray()
        try:
            while chunk := await file.read(64 * 1024):
                content.extend(chunk)
                if len(content) > _CSV_MAX_BYTES:
                    raise HTTPException(status_code=413, detail="CSV exceeds the 5 MiB limit")
        finally:
            await file.close()
        try:
            trades = _parse_diagnostic_csv(bytes(content))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        with DiagnosticsStore() as store:
            result = store.import_csv_trades(user_id, trades)
        if result is None:
            raise HTTPException(status_code=404, detail="User not found")
        return CsvTradeImportResponse(
            **result, totalRows=len(trades), sourceId="csv",
        )
