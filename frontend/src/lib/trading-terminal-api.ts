import { authHeaders } from "@/lib/apiAuth";

export const TERMINAL_USER_ID = "user-123";

export interface Mt5ConnectionStatus {
  userId: string;
  terminalConnected: boolean;
  lastTickTime: string | null;
  ticker: { bid?: number; ask?: number; last?: number } | null;
  positionsCount: number;
  pendingOrdersCount: number;
  latencyMs: number | null;
  errorCode: number | null;
}

export interface Mt5Bar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  tickVolume: number;
  spread: number;
  symbol: string;
  timeframe: string;
}

export interface Mt5Position { ticket: number | null; symbol: string; side: "buy" | "sell"; volume: number; price_open: number; price_current: number; sl: number; tp: number; profit: number; time: number }
export interface Mt5Execution { deal_id: string; order_id: string; symbol: string; volume: number; price: number; profit: number; time: number }
export interface Mt5LiveSnapshot {
  status: "ok";
  connected: true;
  capturedAt: string;
  account: { login: number; name: string; server: string; currency: string; balance: number; equity: number; margin: number; margin_free: number; margin_level: number; leverage: number; is_demo: boolean };
  quote: { bid: number; ask: number; last?: number; spread?: number; time: number };
  symbol: string;
  timeframe: string;
  bars: Array<{ time: number; open: number; high: number; low: number; close: number; tick_volume?: number; real_volume?: number; spread?: number }>;
  positions: Mt5Position[];
  orders: unknown[];
  executions: Mt5Execution[];
}

export interface McpToken { tokenId: string; userId: string; provider: string; expiresAt: string; createdAt: string; isValid: boolean }
export interface AutoTradeEntryAreaCandidate { id: string; type: string; direction: "BULLISH" | "BEARISH"; low: number; high: number; score: number; distance: number; freshness: number; confluenceCount: number; reactionStatus: "WAITING_RETEST" | "TOUCHED" | "REACTION_CONFIRMED" | "INVALIDATED"; ageCandles: number; mitigationCount: number; reason: string }
export interface AutoTradeRunnerStatus { running: boolean; state: string; message: string; symbol: string | null; timeframe: string | null; lastCandleAt: string | null; lastDecision: "BUY" | "SELL" | "HOLD" | null; lastOrderId: string | null; lastError: string | null; selectedStrategyId: string | null; decisionReason: string | null; orderType: string | null; entryPrice: number | null; stopLoss: number | null; takeProfit: number | null; selectedEntryAreaType: string | null; selectedEntryAreaId: string | null; selectedEntryAreaLow: number | null; selectedEntryAreaHigh: number | null; selectedEntryAreaScore: number | null; selectedEntryAreaReason: string | null; entryAreaCandidates: AutoTradeEntryAreaCandidate[] }
export interface AutoSelectionStatus { modeEnabled: boolean; status: "READY" | "WARMING_UP" | "BLOCKED"; symbol: string; analysisTimeframe: string; generatedAt: string; selectedStrategyId: string | null; reason: string; marketContext: { regime: string; trend: string; volatility: string; session: string; spreadPips: number; close: number; emaFast: number | null; emaSlow: number | null; rsi: number | null; atr: number | null; volumeRatio: number | null; barCount: number }; candidates: Array<{ id: string; name: string; score: number; confidence: number; recommendation: "SELECTED" | "ELIGIBLE" | "BLOCKED"; blockedBy: string | null }> }
export interface Mt5Configuration {
  loginMasked: string; login: number; passwordConfigured: boolean; server: string;
  terminalPath: string; profile: "paper" | "live-readonly" | "live"; symbolSuffix: string;
  timeout: number; maxOrderVolume: number; maxOrderNotionalUsd: number; configPath: string;
}
export type Mt5ConfigurationInput = Omit<Mt5Configuration, "loginMasked" | "passwordConfigured" | "configPath"> & { password: string };

export interface AutoTradeConfig {
  id: string;
  userId: string;
  symbol: string;
  timeframe: string;
  strategy: string;
  riskPerTrade: number;
  dailyLossLimit: number;
  paperMode: boolean;
  robotControls: { enabled: boolean; lotSize: number; stopLossPips: number; takeProfitPips: number };
  createdAt: string;
  updatedAt: string;
}

export interface ExecutionLog {
  id: string;
  level: "INFO" | "SIGNAL" | "RISK" | "ERROR";
  status: "MONITORING" | "PENDING" | "EXECUTED" | "REJECTED" | "CLOSED" | "FAILED";
  message: string;
  symbol: string | null;
  direction: "BUY" | "SELL" | null;
  lotSize: number | null;
  price: number | null;
  stopLoss: number | null;
  takeProfit: number | null;
  brokerOrderId: string | null;
  timestamp: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    const detail = contentType.includes("application/json") ? await response.json().catch(() => ({})) : {};
    throw new Error(detail.detail?.error || detail.detail || (contentType.includes("text/html") ? "Backend API belum berjalan atau proxy belum tersambung" : `HTTP ${response.status}`));
  }
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) throw new Error("Backend API mengembalikan HTML, bukan JSON. Pastikan backend port 8899 berjalan.");
  return response.json() as Promise<T>;
}

export const terminalApi = {
  connection: () => request<Mt5ConnectionStatus>("/mt5/connection/status"),
  liveSnapshot: (symbol: string, timeframe: string) => request<Mt5LiveSnapshot>(`/mt5/live/snapshot?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=80`),
  generateMcpToken: (expiresHours: number) => request<McpToken>(`/mt5/token/generate?expires_hours=${expiresHours}`, { method: "POST" }),
  activeMcpToken: () => request<McpToken | null>(`/mt5/token/active?user_id=${encodeURIComponent(TERMINAL_USER_ID)}`),
  revokeMcpToken: (tokenId: string) => request<void>(`/mt5/token/${encodeURIComponent(tokenId)}`, { method: "DELETE" }),
  mt5Configuration: () => request<Mt5Configuration>("/mt5/configuration"),
  saveMt5Configuration: (configuration: Mt5ConfigurationInput) => request<Mt5Configuration>("/mt5/configuration", { method: "PUT", body: JSON.stringify(configuration) }),
  runnerStatus: () => request<AutoTradeRunnerStatus>("/mt5/auto-trade/status"),
  selectionStatus: (symbol = "XAUUSD") => request<AutoSelectionStatus>(`/auto-selection/status?user_id=default&symbol=${encodeURIComponent(symbol)}`),
  startRunner: (body: { symbol: string; timeframe: string; lotSize: number; stopLossPips: number; takeProfitPips: number; paperMode: boolean }) => request<AutoTradeRunnerStatus>("/mt5/auto-trade/start", { method: "POST", body: JSON.stringify(body) }),
  stopRunner: () => request<AutoTradeRunnerStatus>("/mt5/auto-trade/stop", { method: "POST" }),
  configurations: () => request<AutoTradeConfig[]>(`/auto-trade/configurations?userId=${TERMINAL_USER_ID}`),
  logs: (symbol: string) => request<ExecutionLog[]>(`/auto-trade/execution-logs?userId=${TERMINAL_USER_ID}&symbol=${encodeURIComponent(symbol)}&limit=100`),
  saveConfiguration: (config: AutoTradeConfig | null, values: Omit<AutoTradeConfig, "id" | "userId" | "createdAt" | "updatedAt">) =>
    config
      ? request<AutoTradeConfig>(`/auto-trade/configurations/${config.id}?userId=${TERMINAL_USER_ID}`, { method: "PUT", body: JSON.stringify(values) })
      : request<AutoTradeConfig>("/auto-trade/configurations", { method: "POST", body: JSON.stringify({ userId: TERMINAL_USER_ID, ...values }) }),
};
