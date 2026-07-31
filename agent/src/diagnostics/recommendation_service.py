"""Deterministic improvement recommendations derived from persisted loss patterns."""

from __future__ import annotations

from dataclasses import dataclass

from src.diagnostics.store import DiagnosticsStore


@dataclass(frozen=True)
class _RecommendationTemplate:
    title: str
    action: str
    effort: str
    steps: tuple[str, ...]
    validation_target: str
    guardrail: str


_TEMPLATES = {
    "TREND": _RecommendationTemplate(
        "Require aligned trend confirmation",
        "Require the higher-timeframe trend and EMA alignment to agree before opening a position.",
        "MEDIUM",
        (
            "Read the higher-timeframe trend before evaluating an entry signal.",
            "Require trend direction and EMA alignment to agree with the proposed side.",
            "Reject the entry when either confirmation is mixed or opposite.",
        ),
        "Reduce counter-trend loss share below 30% over the next 100 trades.",
        "Do not relax the existing spread, exposure, or stop-loss controls.",
    ),
    "REGIME": _RecommendationTemplate(
        "Add a ranging-market entry gate",
        "Block trend entries when regime classification is ranging and volatility lacks expansion.",
        "MEDIUM",
        (
            "Calculate the current regime before running directional entry logic.",
            "Compare ATR with its rolling median when the regime is classified as ranging.",
            "Skip directional entries until regime or volatility confirms expansion.",
        ),
        "Cut ranging-market losses by at least 25% without reducing breakout participation.",
        "Keep breakout handling separate so the gate does not block confirmed expansion.",
    ),
    "SESSION": _RecommendationTemplate(
        "Reduce risk during Asia session",
        "Reduce position risk during weak sessions until evidence shows performance recovery.",
        "LOW",
        (
            "Identify entries using the existing session classifier.",
            "Apply a conservative risk multiplier before calculating position size.",
            "Restore normal risk automatically when the weak session ends.",
        ),
        "Keep weak-session drawdown below 60% of its current baseline for four weeks.",
        "Never increase another session's risk to compensate for reduced exposure.",
    ),
    "MOMENTUM": _RecommendationTemplate(
        "Set a minimum momentum threshold",
        "Require sufficient normalized volume and RSI expansion before confirming entries.",
        "LOW",
        (
            "Normalize entry volume against its configured rolling window.",
            "Confirm RSI is expanding in the direction of the signal.",
            "Reject signals that fail either momentum condition.",
        ),
        "Reduce weak-momentum loss share below 6% while preserving valid signals.",
        "Validate thresholds in replay before applying them to live execution.",
    ),
}

_PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}


class DiagnosticRecommendationService:
    """Map the latest user-scoped pattern evidence to actionable controls."""

    def __init__(self, store: DiagnosticsStore) -> None:
        self.store = store

    @staticmethod
    def calculate_priority(severity: str, loss_share: float) -> str:
        """Classify recommendation urgency from normalized pattern evidence."""
        normalized_severity = severity.strip().upper()
        if normalized_severity not in {"HIGH", "MEDIUM", "LOW"}:
            raise ValueError(f"Unsupported pattern severity: {severity}")
        if not 0 <= loss_share <= 100:
            raise ValueError("loss_share must be between 0 and 100")
        if normalized_severity == "HIGH" and loss_share >= 40:
            return "CRITICAL"
        if normalized_severity in {"HIGH", "MEDIUM"}:
            return "HIGH"
        return "MEDIUM"

    @staticmethod
    def calculate_expected_impact(loss_share: float, confidence: float) -> float:
        """Estimate addressable loss share, capped to avoid overstating impact."""
        if not 0 <= loss_share <= 100:
            raise ValueError("loss_share must be between 0 and 100")
        if not 0 <= confidence <= 100:
            raise ValueError("confidence must be between 0 and 100")
        return round(min(50.0, loss_share * confidence / 200), 2)

    def list_recommendations(
        self, user_id: str, priority_filter: str | None = None,
    ) -> dict[str, object]:
        analysis = self.store.loss_pattern_analysis(user_id)
        status_overrides = self.store.recommendation_statuses(user_id)
        generated_at = str(analysis["generatedAt"])
        recommendations: list[dict[str, object]] = []
        for pattern in analysis["patterns"]:
            category = str(pattern["category"])
            template = _TEMPLATES.get(category)
            if template is None:
                continue
            share = float(pattern["lossPercentage"])
            confidence = float(pattern["confidence"])
            severity = str(pattern["severity"])
            recommendation_priority = self.calculate_priority(severity, share)
            expected_impact = self.calculate_expected_impact(share, confidence)
            recommendation_id = f"rec_{pattern['id']}"
            recommendations.append({
                "id": recommendation_id,
                "title": template.title,
                "summary": (
                    f"{pattern['name']} accounts for {share:g}% of losses in the latest "
                    "persisted analysis period."
                ),
                "action": template.action,
                "patternId": str(pattern["id"]),
                "patternName": str(pattern["name"]),
                "priority": recommendation_priority,
                "status": status_overrides.get(
                    recommendation_id, "READY" if confidence >= 75 else "REVIEW",
                ),
                "expectedImpact": expected_impact,
                "evidenceLosses": int(pattern["lossCount"]),
                "confidence": confidence,
                "effort": template.effort,
                "steps": list(template.steps),
                "validationTarget": template.validation_target,
                "guardrail": template.guardrail,
            })
        if priority_filter is not None:
            recommendations = [
                recommendation
                for recommendation in recommendations
                if recommendation["priority"] == priority_filter
            ]
        recommendations.sort(key=lambda item: (
            _PRIORITY_ORDER[str(item["priority"])],
            -float(item["expectedImpact"]),
            -float(item["confidence"]),
            str(item["title"]),
        ))
        return {"recommendations": recommendations, "generatedAt": generated_at}

    def get_recommendation(
        self, user_id: str, recommendation_id: str,
    ) -> dict[str, object] | None:
        """Return one recommendation from the user's latest pattern snapshot."""
        payload = self.list_recommendations(user_id)
        return next(
            (
                recommendation
                for recommendation in payload["recommendations"]
                if recommendation["id"] == recommendation_id
            ),
            None,
        )

    def generate_and_persist(self, user_id: str) -> dict[str, object]:
        """Generate and atomically persist the latest user-scoped recommendations."""
        payload = self.list_recommendations(user_id)
        self.store.replace_recommendations(
            user_id,
            str(payload["generatedAt"]),
            list(payload["recommendations"]),
        )
        return payload

    def update_recommendation_status(
        self, user_id: str, recommendation_id: str, status: str,
    ) -> dict[str, object] | None:
        """Persist APPLIED or reopen an existing user-scoped recommendation."""
        recommendation = self.get_recommendation(user_id, recommendation_id)
        if recommendation is None:
            return None
        self.store.set_recommendation_applied(
            user_id, recommendation_id, applied=status == "APPLIED",
        )
        return self.get_recommendation(user_id, recommendation_id)