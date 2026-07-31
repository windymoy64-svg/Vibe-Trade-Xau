export type ImprovementEventStatus = "PLANNED" | "APPLIED" | "MONITORING" | "VALIDATED";

export interface ImprovementTimelineEvent {
  id: string;
  recommendationId: string;
  title: string;
  description: string;
  status: ImprovementEventStatus;
  occurredAt: string;
  owner: string;
  evidenceNote?: string;
}

export interface LossReductionPoint {
  label: string;
  lossRate: number;
  tradeCount: number;
}

export type ImprovementActivityType = "NOTE" | "STATUS_CHANGE" | "EVIDENCE";

export interface ImprovementActivity {
  id: string;
  type: ImprovementActivityType;
  message: string;
  actor: string;
  occurredAt: string;
  recommendationId: string;
}

export type SuccessMetricStatus = "ACHIEVED" | "ON_TRACK" | "AT_RISK";

export interface SuccessMetric {
  id: string;
  label: string;
  current: string;
  target: string;
  progress: number;
  status: SuccessMetricStatus;
  detail: string;
}

export interface ImprovementSummary {
  tracked: number;
  active: number;
  validated: number;
  validationCoverage: number;
  bestObservedChange: number;
  bestObservedLabel: string;
}

export interface DiagnosticImprovementProgressData {
  summary: ImprovementSummary;
  timeline: ImprovementTimelineEvent[];
  lossReduction: LossReductionPoint[];
  successMetrics: SuccessMetric[];
  activities: ImprovementActivity[];
  generatedAt: string;
}

export const improvementTimelineStub: ImprovementTimelineEvent[] = [
  {
    id: "event_trend_validated",
    recommendationId: "rec_trend_confirmation",
    title: "Trend confirmation gate validated",
    description: "Higher-timeframe trend and EMA alignment are now required before entry.",
    status: "VALIDATED",
    occurredAt: "2026-07-29T14:30:00Z",
    owner: "Strategy team",
    evidenceNote: "Counter-trend loss share decreased by 18 percentage points.",
  },
  {
    id: "event_asia_monitoring",
    recommendationId: "rec_asia_risk",
    title: "Asia-session risk reduction deployed",
    description: "A 0.6 position-risk multiplier is active during Asia trading hours.",
    status: "MONITORING",
    occurredAt: "2026-07-24T09:15:00Z",
    owner: "Risk controls",
    evidenceNote: "Collecting trades for the four-week validation window.",
  },
  {
    id: "event_regime_applied",
    recommendationId: "rec_regime_gate",
    title: "Ranging-market gate applied in replay",
    description: "Directional signals are blocked when regime and volatility confirmation disagree.",
    status: "APPLIED",
    occurredAt: "2026-07-20T11:00:00Z",
    owner: "Replay pipeline",
  },
  {
    id: "event_momentum_planned",
    recommendationId: "rec_momentum_floor",
    title: "Momentum threshold queued for review",
    description: "Volume normalization and RSI expansion thresholds await replay approval.",
    status: "PLANNED",
    occurredAt: "2026-07-18T16:45:00Z",
    owner: "Diagnostics review",
  },
];

export const lossReductionStub: LossReductionPoint[] = [
  { label: "Baseline", lossRate: 45.2, tradeCount: 248 },
  { label: "Week 1", lossRate: 43.8, tradeCount: 61 },
  { label: "Week 2", lossRate: 41.5, tradeCount: 68 },
  { label: "Week 3", lossRate: 39.9, tradeCount: 72 },
  { label: "Week 4", lossRate: 37.1, tradeCount: 75 },
];

export const successMetricsStub: SuccessMetric[] = [
  { id: "metric-trend", label: "Counter-trend loss share", current: "27%", target: "< 30%", progress: 100, status: "ACHIEVED" as const, detail: "Based on the latest 100 validated trades." },
  { id: "metric-regime", label: "Ranging-market losses", current: "−19%", target: "−25%", progress: 76, status: "ON_TRACK" as const, detail: "Reduction relative to the diagnosed baseline." },
  { id: "metric-asia", label: "Asia-session drawdown", current: "72%", target: "< 60% baseline", progress: 48, status: "AT_RISK" as const, detail: "Needs more evidence before the review window closes." },
  { id: "metric-momentum", label: "Weak-momentum loss share", current: "7.2%", target: "< 6%", progress: 35, status: "AT_RISK" as const, detail: "Replay validation is not complete yet." },
];

export const improvementActivityStub: ImprovementActivity[] = [
  { id: "activity-1", type: "EVIDENCE", message: "Added 75 trades to the Asia-session validation window.", actor: "Diagnostics engine", occurredAt: "2026-07-31T08:10:00Z", recommendationId: "rec_asia_risk" },
  { id: "activity-2", type: "NOTE", message: "Replay confirms breakout handling remains unaffected by the regime gate.", actor: "Strategy team", occurredAt: "2026-07-30T15:20:00Z", recommendationId: "rec_regime_gate" },
  { id: "activity-3", type: "STATUS_CHANGE", message: "Marked trend confirmation recommendation as validated.", actor: "Trader", occurredAt: "2026-07-29T14:30:00Z", recommendationId: "rec_trend_confirmation" },
  { id: "activity-4", type: "NOTE", message: "Momentum threshold remains pending replay approval.", actor: "Diagnostics review", occurredAt: "2026-07-28T11:45:00Z", recommendationId: "rec_momentum_floor" },
];

export const diagnosticImprovementProgressStub: DiagnosticImprovementProgressData = {
  summary: {
    tracked: 4,
    active: 3,
    validated: 1,
    validationCoverage: 75,
    bestObservedChange: -18,
    bestObservedLabel: "Counter-trend loss share",
  },
  timeline: improvementTimelineStub,
  lossReduction: lossReductionStub,
  successMetrics: successMetricsStub,
  activities: improvementActivityStub,
  generatedAt: "2026-07-31T08:30:00Z",
};