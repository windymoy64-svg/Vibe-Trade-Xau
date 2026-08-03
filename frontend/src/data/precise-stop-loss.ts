// XAUUSD constants — most brokers use 5-digit pricing (1 pip = 0.10 USD)
const XAUUSD_PIP_SIZE = 0.1;
const XAUUSD_DIGITS = 5;

/** Convert pips to points for XAUUSD (1 pip = 10 points on 5-digit brokers). */
export function pipsToPoints(pips: number): number {
  return pips * 10;
}

/** Convert points to pips for XAUUSD. */
export function pointsToPips(points: number): number {
  return points / 10;
}

/** Calculate pip distance between two prices for XAUUSD (5-digit format). */
export function priceDistanceInPips(priceA: number, priceB: number): number {
  const diff = Math.abs(priceA - priceB);
  return Number((diff / XAUUSD_PIP_SIZE).toFixed(2));
}

/** Round price to XAUUSD broker digit precision (typically 5 digits). */
export function roundToXauusdPrecision(price: number): number {
  const factor = Math.pow(10, XAUUSD_DIGITS);
  return Math.round(price * factor) / factor;
}

export type StopLossSignalStatus = "VALID" | "REVIEW" | "INVALID";

export interface PreciseStopLossSignal {
  id: string;
  symbol: string;
  direction: "BUY" | "SELL";
  timeframe: string;
  entry: number;
  stopLoss: number;
  currentPrice: number;
  distancePips: number;
  riskAmount: number;
  riskPercent: number;
  lotSize: number;
  acrZone: { low: number; high: number; status: "FRESH" | "MITIGATED" };
  bufferPips: number;
  status: StopLossSignalStatus;
  confidence: number;
  generatedAt: string;
  reasons: string[];
}

export const preciseStopLossSignals: PreciseStopLossSignal[] = [
  { id: "sl-signal-1842", symbol: "XAUUSD", direction: "BUY", timeframe: "M5", entry: 2384.85, stopLoss: 2382.5, currentPrice: 2389.78, distancePips: 23.5, riskAmount: 99.88, riskPercent: 1, lotSize: 0.42, acrZone: { low: 2382.8, high: 2385.4, status: "FRESH" }, bufferPips: 3, status: "VALID", confidence: 94, generatedAt: "2026-08-03T08:42:10Z", reasons: ["SL below fresh bullish ACR low", "3-pip XAUUSD buffer applied", "Risk remains within 1% mandate"] },
  { id: "sl-signal-1841", symbol: "XAUUSD", direction: "SELL", timeframe: "M15", entry: 2392.1, stopLoss: 2398.1, currentPrice: 2389.98, distancePips: 60, riskAmount: 96, riskPercent: 0.96, lotSize: 0.16, acrZone: { low: 2390.2, high: 2397.8, status: "MITIGATED" }, bufferPips: 3, status: "REVIEW", confidence: 72, generatedAt: "2026-08-03T08:36:11Z", reasons: ["Bearish ACR zone has prior mitigation", "SL remains above zone high", "Manual structure review required"] },
];
