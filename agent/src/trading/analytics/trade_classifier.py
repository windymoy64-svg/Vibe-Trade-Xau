"""Explainable, rule-based replay trade classification."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AnalyzedTrade:
    trade_id: str
    symbol: str
    side: str
    entry_time: Any
    exit_time: Any
    entry_price: float
    exit_price: float
    holding_candles: int
    profit: float
    r_multiple: float
    signal: Any
    decision: Any
    risk_approval: str
    volume: float
    sl: float | None
    tp: float | None
    confidence: float | None
    replay_timestamp: Any
    trade_label: str
    outcome_reason: str
    close_reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class TradeClassifier:
    """Classify trades without fitting data or changing strategy parameters."""

    def classify(self, trade: object) -> AnalyzedTrade:
        signal = _mapping(_get(trade, "signal", {}))
        decision = _mapping(_get(trade, "decision", {}))
        reasons = _reason_codes(signal) | _reason_codes(decision)
        confidence = _optional_float(signal.get("confidence"))
        profit = float(_get(trade, "profit", 0.0))
        r_multiple = float(_get(trade, "r_multiple", 0.0))
        close_reason = str(_get(trade, "close_reason", "UNKNOWN")).upper()
        sl = _optional_float(_get(trade, "sl"))
        tp = _optional_float(_get(trade, "tp"))
        entry = float(_get(trade, "entry_price"))
        planned_rr = _planned_rr(entry, sl, tp)

        label = self._setup_label(reasons)
        if profit < 0:
            outcome_reason = self._loss_reason(
                close_reason, reasons, confidence, planned_rr, int(_get(trade, "holding_candles", 0)), r_multiple
            )
        elif profit > 0:
            outcome_reason = self._win_reason(label, reasons, confidence, planned_rr, r_multiple)
        else:
            outcome_reason = "Unknown"

        exit_time = _get(trade, "exit_time")
        return AnalyzedTrade(
            trade_id=str(_get(trade, "trade_id")),
            symbol=str(_get(trade, "symbol")),
            side=str(_get(trade, "side")),
            entry_time=_get(trade, "entry_time"),
            exit_time=exit_time,
            entry_price=entry,
            exit_price=float(_get(trade, "exit_price")),
            holding_candles=int(_get(trade, "holding_candles", 0)),
            profit=profit,
            r_multiple=r_multiple,
            signal=signal,
            decision=decision,
            # A closed replay trade could only originate from an approved plan.
            risk_approval="APPROVED",
            volume=float(_get(trade, "volume", 0.0)),
            sl=sl,
            tp=tp,
            confidence=confidence,
            replay_timestamp=exit_time,
            trade_label=label,
            outcome_reason=outcome_reason,
            close_reason=close_reason,
        )

    @staticmethod
    def _setup_label(reasons: set[str]) -> str:
        if _contains(reasons, "REVERSAL"):
            return "Reversal"
        if _contains(reasons, "BREAKOUT"):
            return "Breakout"
        if _contains(reasons, "PULLBACK"):
            return "Pullback"
        if _contains(reasons, "MOMENTUM", "MACD"):
            return "Momentum"
        if _contains(reasons, "COUNTER_TREND"):
            return "Counter Trend"
        if _contains(reasons, "TREND", "EMA"):
            return "Trend Following"
        return "Unknown"

    @staticmethod
    def _loss_reason(
        close: str, reasons: set[str], confidence: float | None, rr: float | None, holding: int, r_multiple: float
    ) -> str:
        if close == "SL" or r_multiple <= -0.95:
            return "Stopped Out"
        if rr is not None and rr < 1.0:
            return "Low RR"
        if confidence is not None and confidence < 0.55:
            return "Weak Trend"
        if _contains(reasons, "LOW_VOLUME", "VOLUME_WEAK"):
            return "Low Volume"
        if _contains(reasons, "HIGH_VOLATILITY", "VOLATILE"):
            return "High Volatility"
        if _contains(reasons, "RANGE", "SIDEWAYS"):
            return "Range Market"
        if holding <= 1:
            return "Late Entry"
        return "Unknown"

    @staticmethod
    def _win_reason(
        label: str, reasons: set[str], confidence: float | None, rr: float | None, r_multiple: float
    ) -> str:
        if label == "Pullback":
            return "Pullback Success"
        if label in {"Trend Following", "Breakout"}:
            return "Trend Continuation"
        if label == "Momentum" or _contains(reasons, "MOMENTUM", "MACD"):
            return "Momentum"
        if (rr is not None and rr >= 1.5) or r_multiple >= 1.5:
            return "Good RR"
        if confidence is not None and confidence >= 0.7:
            return "Strong Trend"
        return "Strong Trend" if r_multiple >= 1.0 else "Unknown"


def _get(value: object, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, Mapping) else getattr(value, key, default)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return {} if value is None else {"value": str(value)}


def _reason_codes(value: Mapping[str, Any]) -> set[str]:
    raw = value.get("reason_codes", ())
    return {str(item).upper() for item in raw} if isinstance(raw, (list, tuple, set)) else set()


def _contains(reasons: set[str], *tokens: str) -> bool:
    return any(token in reason for reason in reasons for token in tokens)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _planned_rr(entry: float, sl: float | None, tp: float | None) -> float | None:
    risk = abs(entry - sl) if sl is not None else 0.0
    return abs(tp - entry) / risk if tp is not None and risk > 0 else None
