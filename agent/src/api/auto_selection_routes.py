"""Read endpoint and in-memory publication store for strategy auto-selection."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, StrictBool

from src.api.security import require_local_or_auth
from src.trading.auto_selection import MarketIndicatorSnapshot, StrategySelectionResult


@dataclass(frozen=True, slots=True)
class AutoSelectionStatus:
    user_id: str
    snapshot: MarketIndicatorSnapshot
    selection: StrategySelectionResult
    session: str
    spread_pips: float


class AutoSelectionStatusStore:
    """Keep the latest immutable evaluation for each user and symbol."""

    def __init__(self) -> None:
        self._statuses: dict[tuple[str, str], AutoSelectionStatus] = {}
        self._modes: dict[str, tuple[bool, str]] = {}
        self._lock = threading.RLock()

    def publish(
        self,
        user_id: str,
        snapshot: MarketIndicatorSnapshot,
        selection: StrategySelectionResult,
        *,
        session: str,
        spread_pips: float,
    ) -> AutoSelectionStatus:
        normalized_user = str(user_id or "").strip()
        if not normalized_user:
            raise ValueError("user_id is required")
        if snapshot.symbol != selection.symbol or snapshot.timeframe != selection.timeframe:
            raise ValueError("snapshot and selection market context must match")
        if snapshot.timestamp.isoformat() != selection.market_timestamp:
            raise ValueError("snapshot and selection timestamps must match")
        if spread_pips < 0:
            raise ValueError("spread must not be negative")

        status = AutoSelectionStatus(
            user_id=normalized_user,
            snapshot=snapshot,
            selection=selection,
            session=str(session or "UNKNOWN").strip().upper() or "UNKNOWN",
            spread_pips=spread_pips,
        )
        with self._lock:
            self._statuses[(normalized_user, snapshot.symbol)] = status
        return status

    def latest(self, user_id: str, symbol: str | None = None) -> AutoSelectionStatus | None:
        normalized_user = str(user_id or "").strip()
        normalized_symbol = str(symbol or "").strip().upper()
        with self._lock:
            if normalized_symbol:
                return self._statuses.get((normalized_user, normalized_symbol))
            user_statuses = [
                status
                for (stored_user, _), status in self._statuses.items()
                if stored_user == normalized_user
            ]
        return max(user_statuses, key=lambda item: item.snapshot.timestamp, default=None)

    def set_enabled(self, user_id: str, enabled: bool) -> tuple[bool, str]:
        normalized_user = str(user_id or "").strip()
        if not normalized_user:
            raise ValueError("user_id is required")
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._modes[normalized_user] = (enabled, updated_at)
        return enabled, updated_at

    def mode(self, user_id: str) -> tuple[bool, str | None]:
        with self._lock:
            return self._modes.get(str(user_id or "").strip(), (False, None))

    def clear(self) -> None:
        with self._lock:
            self._statuses.clear()
            self._modes.clear()


class MarketContextResponse(BaseModel):
    regime: str
    trend: str
    volatility: str
    session: str
    spreadPips: float
    close: float
    emaFast: float | None
    emaSlow: float | None
    rsi: float | None
    atr: float | None
    volumeRatio: float | None
    barCount: int


class StrategyCandidateResponse(BaseModel):
    id: str
    name: str
    description: str
    score: int
    confidence: int
    recommendation: Literal["SELECTED", "ELIGIBLE", "BLOCKED"]
    matchedConditions: list[str]
    blockedBy: str | None = None


class AutoSelectionStatusResponse(BaseModel):
    modeEnabled: bool
    status: Literal["READY", "WARMING_UP", "BLOCKED"]
    symbol: str
    analysisTimeframe: str
    generatedAt: str
    marketContext: MarketContextResponse
    selectedStrategyId: str | None
    reason: str
    candidates: list[StrategyCandidateResponse]


class ToggleAutoSelectionRequest(BaseModel):
    userId: str = "default"
    enabled: StrictBool


class ToggleAutoSelectionResponse(BaseModel):
    userId: str
    enabled: bool
    updatedAt: str


auto_selection_status_store = AutoSelectionStatusStore()


def publish_auto_selection_status(
    user_id: str,
    snapshot: MarketIndicatorSnapshot,
    selection: StrategySelectionResult,
    *,
    session: str,
    spread_pips: float,
) -> AutoSelectionStatus:
    """Publish a completed evaluation for the status endpoint."""
    return auto_selection_status_store.publish(
        user_id,
        snapshot,
        selection,
        session=session,
        spread_pips=spread_pips,
    )


def register_auto_selection_routes(app: Any) -> None:
    @app.get(
        "/auto-selection/status",
        response_model=AutoSelectionStatusResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def auto_selection_status(
        user_id: str = Query("default", min_length=1, max_length=128),
        symbol: str | None = Query(None, min_length=1, max_length=32),
    ) -> AutoSelectionStatusResponse:
        status = auto_selection_status_store.latest(user_id, symbol)
        if status is None:
            raise HTTPException(status_code=404, detail="Auto-selection status not found")

        snapshot = status.snapshot
        selection = status.selection
        candidates = [
            StrategyCandidateResponse(
                id=candidate.id,
                name=candidate.name,
                description=candidate.description,
                score=candidate.score,
                confidence=candidate.confidence,
                recommendation=candidate.recommendation,
                matchedConditions=list(candidate.matched_conditions),
                blockedBy=" ".join(candidate.blocked_by) or None,
            )
            for candidate in selection.candidates
        ]
        response_status = "WARMING_UP" if not snapshot.ready else (
            "READY" if selection.selected_strategy_id else "BLOCKED"
        )
        mode_enabled, _ = auto_selection_status_store.mode(user_id)
        return AutoSelectionStatusResponse(
            modeEnabled=mode_enabled,
            status=response_status,
            symbol=selection.symbol,
            analysisTimeframe=selection.timeframe,
            generatedAt=selection.market_timestamp,
            marketContext=MarketContextResponse(
                regime=snapshot.regime,
                trend=snapshot.trend,
                volatility=snapshot.volatility,
                session=status.session,
                spreadPips=status.spread_pips,
                close=snapshot.close,
                emaFast=snapshot.ema_fast,
                emaSlow=snapshot.ema_slow,
                rsi=snapshot.rsi,
                atr=snapshot.atr,
                volumeRatio=snapshot.volume_ratio,
                barCount=snapshot.bar_count,
            ),
            selectedStrategyId=selection.selected_strategy_id,
            reason=selection.reason,
            candidates=candidates,
        )

    @app.post(
        "/auto-selection/toggle",
        response_model=ToggleAutoSelectionResponse,
        dependencies=[Depends(require_local_or_auth)],
    )
    async def toggle_auto_selection(
        payload: ToggleAutoSelectionRequest,
    ) -> ToggleAutoSelectionResponse:
        user_id = payload.userId.strip()
        if not user_id or len(user_id) > 128:
            raise HTTPException(status_code=422, detail="Invalid user ID")
        enabled, updated_at = auto_selection_status_store.set_enabled(user_id, payload.enabled)
        return ToggleAutoSelectionResponse(
            userId=user_id,
            enabled=enabled,
            updatedAt=updated_at,
        )
