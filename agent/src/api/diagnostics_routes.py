"""REST endpoints for production trade diagnostics."""

from __future__ import annotations

import csv
import html
import io
from typing import Any, Literal

from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel

from src.api.security import require_local_or_auth
from src.diagnostics.store import DiagnosticsStore


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


class DiagnosticTradeListResponse(BaseModel):
    items: list[dict[str, object]]
    total: int
    limit: int
    offset: int


class DiagnosticExportRequest(BaseModel):
    trade_ids: list[str]
    format: Literal["csv", "pdf"]
    user_id: str = "default"


class SaveDiagnosticFilterRequest(BaseModel):
    user_id: str = "default"
    name: str
    criteria: dict[str, object]


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