"""Composed read-only Phase 12 analytics dashboard."""
from src.aios.observation.analytics.contracts import (
    AnalyticsHealthReport, EvidenceAnalyticsDashboard, EvidenceQualityAnalytics,
    EvidenceTrendAnalytics, PolicyInsights, ReplayAnalytics,
)


def build_analytics_dashboard(
    quality: EvidenceQualityAnalytics, trends: EvidenceTrendAnalytics, policy: PolicyInsights,
    replay: ReplayAnalytics, health: AnalyticsHealthReport,
) -> EvidenceAnalyticsDashboard:
    return EvidenceAnalyticsDashboard(
        quality=quality, trends=trends, policy=policy, replay=replay, health=health,
    )
