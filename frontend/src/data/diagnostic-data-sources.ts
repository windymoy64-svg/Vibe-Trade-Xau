export type DiagnosticSourceStatus = "CONNECTED" | "AVAILABLE" | "ATTENTION";

export interface DiagnosticDataSource {
  id: string;
  name: string;
  type: string;
  description: string;
  status: DiagnosticSourceStatus;
  lastSyncAt?: string;
  importedTrades: number;
  coverage: string[];
}

export const diagnosticDataSourcesStub: DiagnosticDataSource[] = [
  { id: "mt5", name: "MetaTrader 5", type: "Trading terminal", description: "Stream closed trades and entry-time indicator snapshots from the XAUUSD bot.", status: "CONNECTED", lastSyncAt: "2026-07-31T08:24:00Z", importedTrades: 1248, coverage: ["Trade lifecycle", "EMA / RSI / ATR", "Market regime", "Session"] },
  { id: "csv", name: "CSV trade import", type: "File upload", description: "Import historical trades using the diagnostics CSV template.", status: "AVAILABLE", importedTrades: 860, coverage: ["Historical trades", "Entry snapshots", "Suspected reason"] },
  { id: "webhook", name: "Diagnostics webhook", type: "REST API", description: "Send live trade events from an external bot or execution service.", status: "ATTENTION", lastSyncAt: "2026-07-29T16:10:00Z", importedTrades: 315, coverage: ["Live entries", "Trade outcomes", "Custom evidence"] },
];