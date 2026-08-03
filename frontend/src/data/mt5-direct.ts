export type Mt5PipelineStatus = "HEALTHY" | "DEGRADED" | "OFFLINE";
export interface Mt5OhlcBar { time: string; open: number; high: number; low: number; close: number; tickVolume: number }

export interface Mt5DirectPreviewData {
  terminal: {
    name: string;
    broker: string;
    account: string;
    server: string;
    build: string;
    status: Mt5PipelineStatus;
    latencyMs: number;
    lastHeartbeatAt: string;
  };
  metrics: { ticksToday: number; barsIngested: number; tradesAnalyzed: number; diagnosticCoverage: number };
  pipeline: Array<{ id: string; label: string; detail: string; status: Mt5PipelineStatus; updatedAt: string }>;
  trades: Array<{ id: string; ticket: string; direction: "BUY" | "SELL"; result: "TP" | "SL"; regime: string; session: string; cause: string; confidence: number; analyzedAt: string }>;
  ohlc: { symbol: string; timeframe: string; bars: Mt5OhlcBar[] };
}

export const mt5DirectPreview: Mt5DirectPreviewData = {
  terminal: { name: "MT5 Local Terminal", broker: "ICMarkets-Demo", account: "85601234", server: "ICMarketsSC-Demo", build: "4890", status: "HEALTHY", latencyMs: 18, lastHeartbeatAt: "2026-08-03T08:42:10Z" },
  metrics: { ticksToday: 128_442, barsIngested: 18_720, tradesAnalyzed: 84, diagnosticCoverage: 96.4 },
  pipeline: [
    { id: "terminal", label: "MetaTrader5 Python session", detail: "Native terminal_info/account_info available", status: "HEALTHY", updatedAt: "2026-08-03T08:42:10Z" },
    { id: "ticks", label: "XAUUSD tick ingestion", detail: "Bid/ask snapshots streaming at terminal cadence", status: "HEALTHY", updatedAt: "2026-08-03T08:42:10Z" },
    { id: "bars", label: "OHLC bar synchronization", detail: "H4/H1/M15/M5 aligned to broker time", status: "HEALTHY", updatedAt: "2026-08-03T08:42:09Z" },
    { id: "diagnostics", label: "Production diagnostics", detail: "2 trades await complete volume evidence", status: "DEGRADED", updatedAt: "2026-08-03T08:41:58Z" },
  ],
  trades: [
    { id: "trade-841", ticket: "98421", direction: "BUY", result: "SL", regime: "Ranging", session: "Asia", cause: "Regime filter false positive", confidence: 88, analyzedAt: "2026-08-03T09:06:44Z" },
    { id: "trade-840", ticket: "98408", direction: "SELL", result: "TP", regime: "Trending", session: "London", cause: "No failure detected", confidence: 96, analyzedAt: "2026-08-03T07:44:18Z" },
    { id: "trade-839", ticket: "98392", direction: "SELL", result: "SL", regime: "Strong Bull", session: "Asia", cause: "Counter-trend entry", confidence: 92, analyzedAt: "2026-08-03T06:29:12Z" },
  ],
  ohlc: {
    symbol: "XAUUSD",
    timeframe: "M5",
    bars: Array.from({ length: 24 }, (_, index) => {
      const base = 2382 + index * 0.31 + Math.sin(index / 2) * 1.4;
      const close = base + (index % 3 === 0 ? 0.72 : index % 3 === 1 ? -0.38 : 0.24);
      return { time: `2026-08-03T${String(7 + Math.floor(index / 12)).padStart(2, "0")}:${String((index % 12) * 5).padStart(2, "0")}:00Z`, open: base, high: Math.max(base, close) + 0.48, low: Math.min(base, close) - 0.42, close, tickVolume: 840 + index * 37 };
    }),
  },
};
