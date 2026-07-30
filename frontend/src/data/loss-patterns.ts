export interface LossPattern {
  id: string; name: string; category: "TREND" | "REGIME" | "SESSION" | "MOMENTUM";
  description: string; lossCount: number; lossPercentage: number; confidence: number;
  severity: "HIGH" | "MEDIUM" | "LOW"; evidenceTradeIds: string[];
}

export const lossPatternStub: LossPattern[] = [
  { id: "counter-trend", name: "Counter-trend entry", category: "TREND", description: "Entries execute against the dominant trend or with mixed EMA confirmation.", lossCount: 237, lossPercentage: 42, confidence: 91, severity: "HIGH", evidenceTradeIds: ["trade_1048"] },
  { id: "ranging-market", name: "Ranging market exposure", category: "REGIME", description: "Signals trigger inside low-directional ranging conditions.", lossCount: 175, lossPercentage: 31, confidence: 86, severity: "HIGH", evidenceTradeIds: ["trade_1046"] },
  { id: "asia-session", name: "Asia session weakness", category: "SESSION", description: "Loss concentration increases during lower-liquidity Asia hours.", lossCount: 102, lossPercentage: 18, confidence: 78, severity: "MEDIUM", evidenceTradeIds: ["trade_1044"] },
  { id: "weak-momentum", name: "Weak entry momentum", category: "MOMENTUM", description: "Breakout entries lack sufficient volume or RSI follow-through.", lossCount: 50, lossPercentage: 9, confidence: 69, severity: "LOW", evidenceTradeIds: ["trade_1042"] },
];