export type StrategyRecommendation = "SELECTED" | "ELIGIBLE" | "BLOCKED";

export interface StrategyCandidate {
  id: string;
  name: string;
  description: string;
  score: number;
  confidence: number;
  recommendation: StrategyRecommendation;
  matchedConditions: string[];
  blockedBy?: string;
}

export interface StrategyAutoSelectionPreview {
  symbol: string;
  analysisTimeframe: string;
  generatedAt: string;
  marketContext: {
    regime: string;
    trend: string;
    volatility: string;
    session: string;
    spreadPips: number;
  };
  selectedStrategyId: string;
  candidates: StrategyCandidate[];
  guardrails: Array<{ label: string; value: string; passed: boolean }>;
  fixedRisk: {
    riskPerTradePct: number;
    dailyLossLimitPct: number;
    maxOpenPositions: number;
    stopLossRequired: boolean;
    profileName: string;
  };
}

export interface StrategySelectionEvent {
  id: string;
  strategyName: string;
  reason: string;
  selectedAt: string;
}

export const strategyAutoSelectionPreview: StrategyAutoSelectionPreview = {
  symbol: "XAUUSD",
  analysisTimeframe: "H4 bias · M15 execution",
  generatedAt: "2026-08-01T08:45:00Z",
  marketContext: {
    regime: "TRENDING",
    trend: "BULLISH",
    volatility: "NORMAL",
    session: "LONDON",
    spreadPips: 2.1,
  },
  selectedStrategyId: "evidence-trend-guard",
  candidates: [
    {
      id: "evidence-trend-guard",
      name: "Evidence trend guard",
      description: "Follows confirmed higher-timeframe direction while rejecting ranging entries.",
      score: 92,
      confidence: 88,
      recommendation: "SELECTED",
      matchedConditions: ["H4 bullish structure", "EMA alignment confirmed", "London liquidity active"],
    },
    {
      id: "acr-retest",
      name: "ACR retest continuation",
      description: "Waits for an execution-timeframe retest before continuing with the dominant bias.",
      score: 81,
      confidence: 79,
      recommendation: "ELIGIBLE",
      matchedConditions: ["Discount valuation", "Bullish ACR zone valid", "ATR inside operating range"],
    },
    {
      id: "range-mean-reversion",
      name: "Range mean reversion",
      description: "Trades rotation around equilibrium only when a stable ranging regime is present.",
      score: 34,
      confidence: 91,
      recommendation: "BLOCKED",
      matchedConditions: ["Spread inside limit"],
      blockedBy: "Current market regime is TRENDING, not RANGING.",
    },
  ],
  guardrails: [
    { label: "Diagnostics evidence", value: "Sufficient (184 trades)", passed: true },
    { label: "Minimum confidence", value: "88% / 75% required", passed: true },
    { label: "Spread ceiling", value: "2.1 / 3.0 pips", passed: true },
    { label: "Daily loss lock", value: "0.4% / 2.0%", passed: true },
  ],
  fixedRisk: {
    riskPerTradePct: 0.5,
    dailyLossLimitPct: 2,
    maxOpenPositions: 1,
    stopLossRequired: true,
    profileName: "Conservative fixed",
  },
};

export const strategySelectionHistoryPreview: StrategySelectionEvent[] = [
  { id: "selection-1", strategyName: "Evidence trend guard", reason: "Bullish H4 structure and London liquidity produced the highest fit score.", selectedAt: "2026-08-01T08:45:00Z" },
  { id: "selection-2", strategyName: "ACR retest continuation", reason: "Price entered the discount zone while the execution retest remained valid.", selectedAt: "2026-08-01T08:30:00Z" },
];