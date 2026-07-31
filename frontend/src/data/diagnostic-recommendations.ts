export type RecommendationPriority = "CRITICAL" | "HIGH" | "MEDIUM";
export type RecommendationStatus = "READY" | "REVIEW" | "APPLIED";

export interface DiagnosticRecommendation {
  id: string;
  title: string;
  summary: string;
  action: string;
  patternId: string;
  patternName: string;
  priority: RecommendationPriority;
  status: RecommendationStatus;
  expectedImpact: number;
  evidenceLosses: number;
  confidence: number;
  effort: "LOW" | "MEDIUM" | "HIGH";
  steps: string[];
  validationTarget: string;
  guardrail: string;
}

export interface DiagnosticRecommendationsData {
  recommendations: DiagnosticRecommendation[];
  generatedAt: string;
}

export const diagnosticRecommendationsStub: DiagnosticRecommendationsData = {
  recommendations: [
    {
      id: "rec_trend_confirmation",
      title: "Require aligned trend confirmation",
      summary: "Counter-trend entries remain the largest recurring source of stopped trades.",
      action: "Require the higher-timeframe trend and EMA alignment to agree before opening a position.",
      patternId: "counter-trend",
      patternName: "Counter-trend entry",
      priority: "CRITICAL",
      status: "READY",
      expectedImpact: 21,
      evidenceLosses: 237,
      confidence: 91,
      effort: "MEDIUM",
      steps: [
        "Read the higher-timeframe trend before evaluating an entry signal.",
        "Require trend direction and EMA alignment to agree with the proposed side.",
        "Reject the entry when either confirmation is mixed or opposite.",
      ],
      validationTarget: "Reduce counter-trend loss share below 30% over the next 100 trades.",
      guardrail: "Do not relax the existing spread, exposure, or stop-loss controls.",
    },
    {
      id: "rec_regime_gate",
      title: "Add a ranging-market entry gate",
      summary: "Directional signals are firing while price lacks enough directional structure.",
      action: "Block trend entries when regime classification is ranging and ATR is below its rolling median.",
      patternId: "ranging-market",
      patternName: "Ranging market exposure",
      priority: "HIGH",
      status: "REVIEW",
      expectedImpact: 16,
      evidenceLosses: 175,
      confidence: 86,
      effort: "MEDIUM",
      steps: [
        "Calculate the current regime before running directional entry logic.",
        "Compare ATR with its rolling median when the regime is classified as ranging.",
        "Skip directional entries until either regime or volatility confirms expansion.",
      ],
      validationTarget: "Cut ranging-market losses by at least 25% without reducing breakout participation.",
      guardrail: "Keep breakout handling separate so the gate does not block confirmed expansion.",
    },
    {
      id: "rec_asia_risk",
      title: "Reduce risk during Asia session",
      summary: "Lower-liquidity hours show a persistent concentration of losing trades.",
      action: "Reduce position risk by 40% during Asia hours until session performance recovers.",
      patternId: "asia-session",
      patternName: "Asia session weakness",
      priority: "HIGH",
      status: "READY",
      expectedImpact: 9,
      evidenceLosses: 102,
      confidence: 78,
      effort: "LOW",
      steps: [
        "Identify Asia-session entries using the existing session classifier.",
        "Apply a 0.6 risk multiplier before calculating position size.",
        "Restore normal risk automatically when the London session begins.",
      ],
      validationTarget: "Keep Asia-session drawdown below 60% of its current baseline for four weeks.",
      guardrail: "Never increase another session's risk to compensate for reduced Asia exposure.",
    },
    {
      id: "rec_momentum_floor",
      title: "Set a minimum momentum threshold",
      summary: "A smaller cluster of breakouts has insufficient volume and RSI follow-through.",
      action: "Require normalized volume above 1.1 and RSI expansion before confirming breakout entries.",
      patternId: "weak-momentum",
      patternName: "Weak entry momentum",
      priority: "MEDIUM",
      status: "REVIEW",
      expectedImpact: 5,
      evidenceLosses: 50,
      confidence: 69,
      effort: "LOW",
      steps: [
        "Normalize entry volume against its configured rolling window.",
        "Confirm RSI is expanding in the direction of the breakout.",
        "Reject signals that fail either momentum condition.",
      ],
      validationTarget: "Reduce weak-momentum loss share below 6% while preserving at least 80% of valid breakouts.",
      guardrail: "Validate thresholds in replay before applying them to live execution.",
    },
  ],
  generatedAt: "2026-07-31T08:30:00Z",
};