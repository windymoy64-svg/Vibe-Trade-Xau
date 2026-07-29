"""Phase 12 deterministic, evidence-only analytics projections."""
from src.aios.observation.analytics.aggregation import aggregate_evidence_quality, analyze_session_trends
from src.aios.observation.analytics.contracts import (
    AnalyticsHealthReport, EvidenceAnalyticsDashboard, EvidenceQualityAnalytics,
    EvidenceTrendAnalytics, HistoricalReplayComparison, InsightHealth,
    PolicyComplianceSummary, PolicyInsights, ReplayAnalytics, ReplayOutcome, SessionTrendPoint,
)
from src.aios.observation.analytics.dashboard import build_analytics_dashboard
from src.aios.observation.analytics.insights import (
    aggregate_replay_analytics, build_health_report, summarize_policy_insights,
)

__all__ = [
    "AnalyticsHealthReport", "EvidenceAnalyticsDashboard", "EvidenceQualityAnalytics",
    "EvidenceTrendAnalytics", "HistoricalReplayComparison", "InsightHealth",
    "PolicyComplianceSummary", "PolicyInsights", "ReplayAnalytics", "ReplayOutcome",
    "SessionTrendPoint", "aggregate_evidence_quality", "aggregate_replay_analytics",
    "analyze_session_trends", "build_analytics_dashboard", "build_health_report",
    "summarize_policy_insights",
]
