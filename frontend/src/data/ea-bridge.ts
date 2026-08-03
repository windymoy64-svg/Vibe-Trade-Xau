export type EaConnectionStatus = "ONLINE" | "OFFLINE" | "SYNCING";
export type EaBridgeStatus = "ONLINE" | "OFFLINE" | "SYNCING";
export type EaCommandStatus = "SENT" | "ACKED" | "EXECUTED" | "REJECTED";
export type EaFailSafeState = "ACTIVE" | "NORMAL" | "RECOVERED";
export type EaLogLevel = "INFO" | "WARNING" | "ERROR";

export interface EaConnectionRecord {
  id: string;
  label: string;
  broker: string;
  account: string;
  status: EaConnectionStatus;
  lastSeenAt: string;
  latencyMs: number | null;
  platform: string;
  errors: string[];
}

export interface EaCommandRecord {
  id: string;
  action: string;
  type: "BUY" | "SELL" | "CLOSE" | "MODIFY";
  status: EaCommandStatus;
  symbol: string;
  volume: number;
  price: number;
  timestamp: string;
  latencyMs: number;
}

export interface EaExecutionRecord {
  id: string;
  orderId: string;
  action: string;
  status: string;
  direction: "BUY" | "SELL";
  symbol: string;
  terminal: string;
  volume: number;
  price: number;
  currentPrice: number;
  floatingPnl: number;
  sl: number;
  tp: number;
  syncStatus: "SYNCED" | "STALE" | "MISMATCH";
  openedAt: string;
  updatedAt: string;
}

export interface EaLogRecord {
  id: string;
  level: EaLogLevel;
  source: string;
  message: string;
  timestamp: string;
}

export interface EaPendingOrderRecord {
  id: string;
  ticket: string;
  terminal: string;
  symbol: string;
  type: "BUY_LIMIT" | "SELL_LIMIT" | "BUY_STOP" | "SELL_STOP";
  volume: number;
  targetPrice: number;
  currentPrice: number;
  sl: number;
  tp: number;
  expiresAt: string;
  status: "PLACED" | "TRIGGER_NEAR" | "CANCEL_REQUESTED";
  syncStatus: "SYNCED" | "STALE" | "MISMATCH";
}

export interface EaBridgePreviewData {
  engine: {
    id: string;
    tokenId: string;
    status: EaBridgeStatus;
    lastSyncAt: string;
    intervalMs: number;
    timeframe: string;
  };
  market: {
    symbol: string;
    bid: number;
    ask: number;
    digits: number;
    sessionHigh: number;
    sessionLow: number;
    changePercent: number;
    tickAt: string;
  };
  connections: EaConnectionRecord[];
  commands: EaCommandRecord[];
  executions: EaExecutionRecord[];
  pendingOrders: EaPendingOrderRecord[];
  failSafe: {
    state: EaFailSafeState;
    timeoutSeconds: number;
    emergency: {
      sl: number;
      tp: number;
    };
    lastIncidentAt: string | null;
    incidents: number;
    recoveryHistory: string[];
  };
  metrics: {
    online: number;
    total: number;
    syncEvents: number;
    pendingOrders: number;
    openLots: number;
  };
  logs: EaLogRecord[];
}

export const eaBridgePreview: EaBridgePreviewData = {
  engine: {
    id: "EA-BRIDGE-XAUUSD-01",
    tokenId: "vt_ea_7f3a9c",
    status: "ONLINE",
    lastSyncAt: "2026-08-03T08:42:10Z",
    intervalMs: 1000,
    timeframe: "M5",
  },
  market: {
    symbol: "XAUUSD",
    bid: 2389.78,
    ask: 2389.98,
    digits: 2,
    sessionHigh: 2397.42,
    sessionLow: 2376.18,
    changePercent: 0.34,
    tickAt: "2026-08-03T08:42:10Z",
  },
  connections: [
    {
      id: "ea-1",
      label: "EA · Terminal A",
      broker: "ICMarkets-Demo",
      account: "85601234",
      status: "ONLINE",
      lastSeenAt: "2026-08-03T08:42:10Z",
      latencyMs: 24,
      platform: "MetaTrader 5 · build 4890",
      errors: [],
    },
    {
      id: "ea-2",
      label: "EA · VPS Replication",
      broker: "Live ICMarkets",
      account: "12098433",
      status: "OFFLINE",
      lastSeenAt: "2026-08-03T08:40:02Z",
      latencyMs: null,
      platform: "MetaTrader 5 · build 4890",
      errors: ["Bridge handshake expired: no heartbeat for 128s"],
    },
    {
      id: "ea-3",
      label: "EA · Alpari-ECN",
      broker: "Alpari ECN",
      account: "984512",
      status: "SYNCING",
      lastSeenAt: "2026-08-03T08:41:55Z",
      latencyMs: 41,
      platform: "MetaTrader 5 · build 4890",
      errors: [],
    },
  ],
  commands: [
    { id: "cmd-1842", action: "SL+TP modify", type: "MODIFY", status: "ACKED", symbol: "XAUUSD", volume: 0.05, price: 2389.8, timestamp: "2026-08-03T08:40:12Z", latencyMs: 16 },
    { id: "cmd-1841", action: "Partial close 50%", type: "CLOSE", status: "EXECUTED", symbol: "XAUUSD", volume: 0.025, price: 2391.4, timestamp: "2026-08-03T08:38:44Z", latencyMs: 14 },
    { id: "cmd-1840", action: "Buy limit", type: "BUY", status: "EXECUTED", symbol: "XAUUSD", volume: 0.05, price: 2384.25, timestamp: "2026-08-03T08:31:20Z", latencyMs: 21 },
    { id: "cmd-1839", action: "Move SL to BE", type: "MODIFY", status: "REJECTED", symbol: "XAUUSD", volume: 0.05, price: 2384.25, timestamp: "2026-08-03T08:29:58Z", latencyMs: 31 },
  ],
  executions: [
    {
      id: "pos-99712",
      orderId: "ticket-99712",
      action: "OPEN",
      status: "OPEN",
      direction: "BUY",
      symbol: "XAUUSD",
      terminal: "EA Terminal A",
      volume: 0.05,
      price: 2384.25,
      currentPrice: 2389.78,
      floatingPnl: 27.65,
      sl: 2378.25,
      tp: 2396.25,
      syncStatus: "SYNCED",
      openedAt: "2026-08-03T08:31:20Z",
      updatedAt: "2026-08-03T08:42:10Z",
    },
    {
      id: "pos-99718",
      orderId: "ticket-99718",
      action: "OPEN",
      status: "OPEN",
      direction: "SELL",
      symbol: "XAUUSD",
      terminal: "EA Alpari-ECN",
      volume: 0.03,
      price: 2392.1,
      currentPrice: 2389.98,
      floatingPnl: 6.36,
      sl: 2398.1,
      tp: 2380.1,
      syncStatus: "SYNCED",
      openedAt: "2026-08-03T08:36:11Z",
      updatedAt: "2026-08-03T08:42:10Z",
    },
  ],
  pendingOrders: [
    {
      id: "pending-8821",
      ticket: "ticket-8821",
      terminal: "EA Terminal A",
      symbol: "XAUUSD",
      type: "BUY_LIMIT",
      volume: 0.04,
      targetPrice: 2384.85,
      currentPrice: 2389.78,
      sl: 2382.5,
      tp: 2394.25,
      expiresAt: "2026-08-03T16:00:00Z",
      status: "PLACED",
      syncStatus: "SYNCED",
    },
    {
      id: "pending-8824",
      ticket: "ticket-8824",
      terminal: "EA Alpari-ECN",
      symbol: "XAUUSD",
      type: "SELL_STOP",
      volume: 0.03,
      targetPrice: 2386.4,
      currentPrice: 2389.98,
      sl: 2392.4,
      tp: 2374.4,
      expiresAt: "2026-08-03T18:00:00Z",
      status: "TRIGGER_NEAR",
      syncStatus: "SYNCED",
    },
  ],
  failSafe: {
    state: "NORMAL",
    timeoutSeconds: 60,
    emergency: { sl: 10, tp: 20 },
    lastIncidentAt: null,
    incidents: 0,
    recoveryHistory: [],
  },
  metrics: {
    online: 2,
    total: 3,
    syncEvents: 4,
    pendingOrders: 1,
    openLots: 0.08,
  },
  logs: [
    { id: "ea-log-1", level: "INFO", source: "EA Terminal A", message: "Handshake ok · token validated · feed streaming", timestamp: "2026-08-03T08:31:20Z" },
    { id: "ea-log-2", level: "INFO", source: "engine", message: "Buy limit 0.05 XAUUSD@2384.25 routed", timestamp: "2026-08-03T08:33:22Z" },
    { id: "ea-log-3", level: "WARNING", source: "VPS Replication", message: "Heartbeat missed 128s · emergency SL/TP armed", timestamp: "2026-08-03T08:40:02Z" },
    { id: "ea-log-4", level: "INFO", source: "engine", message: "Partial close executed · volume reduced to 0.025", timestamp: "2026-08-03T08:38:44Z" },
  ],
};
