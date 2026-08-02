export type PrecisionWorkflowStatus = "COMPLETE" | "ACTIVE" | "WAITING";

export interface PrecisionExecutionPreview {
  symbol: string;
  currentPrice: number;
  bias: "BULLISH" | "BEARISH" | "NEUTRAL";
  htfTimeframe: string;
  ltfTimeframe: string;
  dataSource: string;
  generatedAt: string;
  setup: {
    direction: "BUY" | "SELL" | "WAIT";
    executionMethod: "LIMIT" | "MARKET" | "NONE";
    status: string;
    entry: number;
    stopLoss: number;
    riskReward: number;
  };
  workflow: Array<{
    id: string;
    label: string;
    detail: string;
    status: PrecisionWorkflowStatus;
  }>;
}

export interface HtfStructureCandle { time: string; open: number; high: number; low: number; close: number; }
export interface HtfStructureMarker { time: string; price: number; type: "BOS" | "CHOCH"; direction: "BULLISH" | "BEARISH"; detail: string; }
export interface LtfSupplyDemandZone {
  id: string;
  type: "SUPPLY" | "DEMAND";
  status: "FRESH" | "MITIGATED";
  startTime: string;
  endTime: string;
  low: number;
  high: number;
}
export interface RacrReversalMarker {
  time: string;
  price: number;
  direction: "BULLISH" | "BEARISH";
  sweepPrice: number;
  reclaimedLevel: number;
}
export interface FvgOverlayZone {
  id: string;
  direction: "BULLISH" | "BEARISH";
  status: "OPEN" | "PARTIAL";
  startTime: string;
  endTime: string;
  low: number;
  high: number;
  acrConfluence: boolean;
  acrZoneId?: string;
  overlapLow?: number;
  overlapHigh?: number;
}
export interface AcrZonePreview {
  id: string;
  direction: "BULLISH" | "BEARISH";
  status: "FRESH" | "INVALID";
  timeframe: string;
  formedAt: string;
  low: number;
  high: number;
  triggerClose: number;
  referenceBoundary: number;
  invalidation?: { time: string; close: number };
}
export interface FibonacciValuationPreview {
  swingLow: number;
  swingHigh: number;
  equilibrium: number;
  currentPrice: number;
  setupZoneMidpoint: number;
  setupDirection: "BUY" | "SELL";
  setupValuation: "PREMIUM" | "DISCOUNT";
  eligible: boolean;
}
export interface OrderTypeRecommendationPreview {
  recommendation: "BUY LIMIT" | "SELL LIMIT" | "MARKET BUY" | "MARKET SELL" | "WAIT";
  status: "RETEST WAITING" | "CONFIRMED" | "BLOCKED";
  currentPrice: number;
  entryPrice: number;
  distancePoints: number;
  checks: Array<{ label: string; passed: boolean; detail: string }>;
}
export interface PrecisionEntryPreview {
  symbol: string;
  direction: "BUY" | "SELL";
  price: number;
  currentPrice: number;
  tickSize: number;
  zoneLow: number;
  zoneHigh: number;
  source: string;
}
export interface TradeLevelsPreview {
  direction: "BUY" | "SELL";
  entry: number;
  zoneBoundary: number;
  bufferPips: number;
  stopLoss: number;
  riskDistance: number;
  targets: Array<{ id: "TP1" | "TP2" | "TP3"; price: number; riskReward: number; source: string }>;
}
export interface TrailingStopPreview {
  direction: "BUY" | "SELL";
  mode: "SIMULATION";
  steps: Array<{ id: string; trigger: string; stopPrice: number; status: "LOCKED" | "NEXT" | "PROJECTED"; detail: string }>;
}
export interface ActionableSignalPreview {
  symbol: string;
  bias: "STRONG BUY" | "STRONG SELL" | "WAIT";
  orderType: "BUY LIMIT" | "SELL LIMIT" | "MARKET BUY" | "MARKET SELL" | "NONE";
  status: "RETEST WAITING" | "HOLD" | "EXIT" | "CANCEL PENDING ORDER";
  entry: number;
  stopLoss: number;
  targets: number[];
  minimumRiskReward: number;
  confidence: number;
  evidence: string[];
}

export const precisionExecutionPreview: PrecisionExecutionPreview = {
  symbol: "XAUUSD",
  currentPrice: 2389.8,
  bias: "BULLISH",
  htfTimeframe: "H4",
  ltfTimeframe: "M15",
  dataSource: "Preview OHLCV · 1,240 candles",
  generatedAt: "2026-08-01T08:46:00Z",
  setup: {
    direction: "BUY",
    executionMethod: "LIMIT",
    status: "RETEST WAITING",
    entry: 2384.25,
    stopLoss: 2378.25,
    riskReward: 2,
  },
  workflow: [
    { id: "structure", label: "HTF structure", detail: "H4 bias and swing map", status: "COMPLETE" },
    { id: "zones", label: "ACR & FVG zones", detail: "M15 confluence scan", status: "ACTIVE" },
    { id: "valuation", label: "Valuation matrix", detail: "Premium / discount gate", status: "WAITING" },
    { id: "execution", label: "Execution plan", detail: "Entry, SL and multi-TP", status: "WAITING" },
  ],
};

export const htfStructurePreview: { candles: HtfStructureCandle[]; markers: HtfStructureMarker[] } = {
  candles: [
    ["Jul 28 00:00", 2365.4, 2372.8, 2361.2, 2370.1], ["Jul 28 04:00", 2370.1, 2378.5, 2368.7, 2376.9], ["Jul 28 08:00", 2376.9, 2380.4, 2371.3, 2373.2], ["Jul 28 12:00", 2373.2, 2382.6, 2372.1, 2380.8], ["Jul 28 16:00", 2380.8, 2388.1, 2378.4, 2386.5], ["Jul 28 20:00", 2386.5, 2389.2, 2379.6, 2381.4], ["Jul 29 00:00", 2381.4, 2385.7, 2375.2, 2377.1], ["Jul 29 04:00", 2377.1, 2384.9, 2374.8, 2383.6], ["Jul 29 08:00", 2383.6, 2391.5, 2381.9, 2389.4], ["Jul 29 12:00", 2389.4, 2395.8, 2387.2, 2393.1], ["Jul 29 16:00", 2393.1, 2394.6, 2384.1, 2386.2], ["Jul 29 20:00", 2386.2, 2390.7, 2380.5, 2382.3], ["Jul 30 00:00", 2382.3, 2388.6, 2379.8, 2387.9], ["Jul 30 04:00", 2387.9, 2397.4, 2386.3, 2395.6], ["Jul 30 08:00", 2395.6, 2402.1, 2392.4, 2399.8], ["Jul 30 12:00", 2399.8, 2401.3, 2390.2, 2392.7], ["Jul 30 16:00", 2392.7, 2396.8, 2384.5, 2386.1], ["Jul 30 20:00", 2386.1, 2391.2, 2381.7, 2389.8],
  ].map(([time, open, high, low, close]) => ({ time: String(time), open: Number(open), high: Number(high), low: Number(low), close: Number(close) })),
  markers: [
    { time: "Jul 28 16:00", price: 2388.1, type: "BOS", direction: "BULLISH", detail: "Previous H4 swing high broken." },
    { time: "Jul 29 04:00", price: 2374.8, type: "CHOCH", direction: "BULLISH", detail: "Bearish pullback failed and structure reclaimed." },
    { time: "Jul 29 12:00", price: 2395.8, type: "BOS", direction: "BULLISH", detail: "Continuation break above liquidity." },
    { time: "Jul 30 16:00", price: 2384.5, type: "CHOCH", direction: "BEARISH", detail: "Short-term internal structure shifted lower." },
  ],
};

export const ltfSupplyDemandPreview: { candles: HtfStructureCandle[]; zones: LtfSupplyDemandZone[]; reversalMarkers: RacrReversalMarker[]; fvgZones: FvgOverlayZone[] } = {
  candles: [
    ["Jul 30 14:00", 2387.2, 2388.4, 2386.5, 2387.9], ["Jul 30 14:15", 2387.9, 2389.1, 2387.3, 2388.8],
    ["Jul 30 14:30", 2388.8, 2390.2, 2388.2, 2389.7], ["Jul 30 14:45", 2389.7, 2391.4, 2389.1, 2390.9],
    ["Jul 30 15:00", 2390.9, 2392.6, 2390.4, 2391.8], ["Jul 30 15:15", 2391.8, 2393.1, 2390.8, 2391.2],
    ["Jul 30 15:30", 2391.2, 2391.7, 2389.5, 2390.1], ["Jul 30 15:45", 2390.1, 2390.6, 2388.4, 2388.9],
    ["Jul 30 16:00", 2388.9, 2389.4, 2386.8, 2387.4], ["Jul 30 16:15", 2387.4, 2387.9, 2385.6, 2386.2],
    ["Jul 30 16:30", 2386.2, 2386.8, 2383.9, 2384.5], ["Jul 30 16:45", 2384.5, 2385.1, 2382.3, 2384.2],
    ["Jul 30 17:00", 2384.2, 2385.3, 2382.8, 2384.8], ["Jul 30 17:15", 2384.8, 2386.7, 2384.2, 2386.1],
    ["Jul 30 17:30", 2386.1, 2387.8, 2385.7, 2387.3], ["Jul 30 17:45", 2387.3, 2389.2, 2386.9, 2388.6],
    ["Jul 30 18:00", 2388.6, 2390.1, 2388.0, 2389.5], ["Jul 30 18:15", 2389.5, 2390.4, 2388.7, 2389.8],
  ].map(([time, open, high, low, close]) => ({ time: String(time), open: Number(open), high: Number(high), low: Number(low), close: Number(close) })),
  zones: [
    { id: "supply-01", type: "SUPPLY", status: "MITIGATED", startTime: "Jul 30 15:00", endTime: "Jul 30 18:15", low: 2391.2, high: 2393.1 },
    { id: "demand-01", type: "DEMAND", status: "FRESH", startTime: "Jul 30 16:30", endTime: "Jul 30 18:15", low: 2382.3, high: 2384.8 },
  ],
  reversalMarkers: [
    { time: "Jul 30 15:15", price: 2393.1, direction: "BEARISH", sweepPrice: 2393.1, reclaimedLevel: 2392.6 },
    { time: "Jul 30 16:45", price: 2382.3, direction: "BULLISH", sweepPrice: 2382.3, reclaimedLevel: 2383.9 },
  ],
  fvgZones: [
    { id: "fvg-bull-01", direction: "BULLISH", status: "OPEN", startTime: "Jul 30 17:00", endTime: "Jul 30 18:15", low: 2384.6, high: 2385.1, acrConfluence: true, acrZoneId: "acr-bull-01", overlapLow: 2384.6, overlapHigh: 2385.1 },
    { id: "fvg-bear-01", direction: "BEARISH", status: "PARTIAL", startTime: "Jul 30 15:30", endTime: "Jul 30 18:15", low: 2389.4, high: 2389.5, acrConfluence: false },
  ],
};

export const acrZonePreview: AcrZonePreview[] = [
  { id: "acr-bull-01", direction: "BULLISH", status: "FRESH", timeframe: "M15", formedAt: "Jul 30 17:00", low: 2382.8, high: 2385.3, triggerClose: 2384.8, referenceBoundary: 2384.5 },
  { id: "acr-bear-01", direction: "BEARISH", status: "INVALID", timeframe: "M15", formedAt: "Jul 30 15:45", low: 2388.4, high: 2390.6, triggerClose: 2388.9, referenceBoundary: 2389.5, invalidation: { time: "Jul 30 18:30", close: 2391.1 } },
];

export const fibonacciValuationPreview: FibonacciValuationPreview = {
  swingLow: 2374.8,
  swingHigh: 2402.1,
  equilibrium: 2388.45,
  currentPrice: 2389.8,
  setupZoneMidpoint: 2384.05,
  setupDirection: "BUY",
  setupValuation: "DISCOUNT",
  eligible: true,
};

export const orderTypeRecommendationPreview: OrderTypeRecommendationPreview = {
  recommendation: "BUY LIMIT",
  status: "RETEST WAITING",
  currentPrice: 2389.8,
  entryPrice: 2384.85,
  distancePoints: 4.95,
  checks: [
    { label: "Price outside zone", passed: true, detail: "Current price remains above the fresh Bullish ACR range." },
    { label: "Discount valuation", passed: true, detail: "Entry midpoint is below HTF equilibrium." },
    { label: "FVG overlap", passed: true, detail: "Open Bullish FVG overlaps the selected ACR zone." },
    { label: "Retest + R-ACR", passed: false, detail: "No confirmation candle inside the zone yet; Market order stays blocked." },
  ],
};

export const precisionEntryPreview: PrecisionEntryPreview = {
  symbol: "XAUUSD",
  direction: "BUY",
  price: 2384.85,
  currentPrice: 2389.8,
  tickSize: 0.00001,
  zoneLow: 2384.6,
  zoneHigh: 2385.1,
  source: "50% FVG equilibrium inside fresh Bullish ACR",
};

export const tradeLevelsPreview: TradeLevelsPreview = {
  direction: "BUY",
  entry: 2384.85,
  zoneBoundary: 2382.8,
  bufferPips: 3,
  stopLoss: 2382.5,
  riskDistance: 2.35,
  targets: [
    { id: "TP1", price: 2389.55, riskReward: 2, source: "Minimum 1:2 RRR" },
    { id: "TP2", price: 2395.8, riskReward: 4.66, source: "Previous HTF swing" },
    { id: "TP3", price: 2402.1, riskReward: 7.34, source: "HTF external liquidity" },
  ],
};

export const trailingStopPreview: TrailingStopPreview = {
  direction: "BUY",
  mode: "SIMULATION",
  steps: [
    { id: "initial", trigger: "Order filled", stopPrice: 2382.5, status: "LOCKED", detail: "Initial ACR low minus 3-pip buffer" },
    { id: "breakeven", trigger: "TP1 reached", stopPrice: 2384.85, status: "NEXT", detail: "Move protection to exact entry" },
    { id: "trail-01", trigger: "New Bullish ACR", stopPrice: 2387.2, status: "PROJECTED", detail: "Trail below latest confirmed fresh zone" },
    { id: "trail-02", trigger: "Continuation BOS", stopPrice: 2391.4, status: "PROJECTED", detail: "Lock profit under the next ACR structure" },
  ],
};

export const actionableSignalPreview: ActionableSignalPreview = {
  symbol: "XAUUSD",
  bias: "STRONG BUY",
  orderType: "BUY LIMIT",
  status: "RETEST WAITING",
  entry: 2384.85,
  stopLoss: 2382.5,
  targets: [2389.55, 2395.8, 2402.1],
  minimumRiskReward: 2,
  confidence: 87,
  evidence: ["H4 bullish structure", "Fresh M15 Bullish ACR", "Discount valuation", "FVG + ACR overlap"],
};
