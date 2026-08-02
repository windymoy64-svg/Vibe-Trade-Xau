export type AutoTradeEngineStatus = "RUNNING" | "PAUSED" | "STOPPED";
export type AutoTradeLogLevel = "INFO" | "SIGNAL" | "RISK";
export type AutoTradeConnectionStatus = "DISCONNECTED" | "CONNECTED" | "ERROR";
export type AutoTradeExecutionStatus = "MONITORING" | "PENDING" | "CLOSED";

export interface AutoTradeLogEntry {
  id: string;
  level: AutoTradeLogLevel;
  message: string;
  timestamp: string;
}

export interface AutoTradePreviewData {
  engineStatus: AutoTradeEngineStatus;
  symbol: string;
  timeframe: string;
  strategy: string;
  riskPerTrade: number;
  dailyLossLimit: number;
  paperMode: boolean;
  apiKeyHint: string;
  apiConnection: {
    provider: string;
    environment: string;
    status: AutoTradeConnectionStatus;
    lastCheckedAt: string | null;
  };
  robotControls: {
    enabled: boolean;
    lotSize: number;
    stopLossPips: number;
    takeProfitPips: number;
    limits: {
      minLot: number;
      maxLot: number;
      minStopLossPips: number;
      maxStopLossPips: number;
      minTakeProfitPips: number;
      maxTakeProfitPips: number;
    };
  };
  currentExecution: {
    id: string;
    status: AutoTradeExecutionStatus;
    direction: "BUY" | "SELL";
    symbol: string;
    entryPrice: number;
    currentPrice: number;
    stopLoss: number;
    takeProfit: number;
    lotSize: number;
    floatingR: number;
    openedAt: string;
    updatedAt: string;
  };
  metrics: {
    signalsToday: number;
    acceptedSignals: number;
    openPositions: number;
    sessionPnl: number;
  };
  logs: AutoTradeLogEntry[];
}

export const autoTradePreviewData: AutoTradePreviewData = {
  engineStatus: "PAUSED",
  symbol: "XAUUSD",
  timeframe: "M15",
  strategy: "Evidence trend guard",
  riskPerTrade: 0.5,
  dailyLossLimit: 2,
  paperMode: true,
  apiKeyHint: "vt_preview_••••••••4f2a",
  apiConnection: {
    provider: "Vibe Broker Gateway",
    environment: "Paper sandbox",
    status: "DISCONNECTED",
    lastCheckedAt: null,
  },
  robotControls: {
    enabled: false,
    lotSize: 0.05,
    stopLossPips: 30,
    takeProfitPips: 60,
    limits: {
      minLot: 0.01,
      maxLot: 1,
      minStopLossPips: 5,
      maxStopLossPips: 250,
      minTakeProfitPips: 10,
      maxTakeProfitPips: 500,
    },
  },
  currentExecution: {
    id: "PREVIEW-1842",
    status: "MONITORING",
    direction: "BUY",
    symbol: "XAUUSD",
    entryPrice: 2384.25,
    currentPrice: 2389.8,
    stopLoss: 2378.25,
    takeProfit: 2396.25,
    lotSize: 0.05,
    floatingR: 0.93,
    openedAt: "2026-08-01T08:38:00Z",
    updatedAt: "2026-08-01T08:46:00Z",
  },
  metrics: {
    signalsToday: 14,
    acceptedSignals: 5,
    openPositions: 0,
    sessionPnl: 1.24,
  },
  logs: [
    { id: "log-1", level: "INFO", message: "Paper engine initialized with XAUUSD M15 controls.", timestamp: "2026-07-31T08:30:00Z" },
    { id: "log-2", level: "SIGNAL", message: "BUY signal held: market regime remained RANGING.", timestamp: "2026-07-31T08:42:00Z" },
    { id: "log-3", level: "RISK", message: "Risk gate confirmed 0.5% exposure and no open position.", timestamp: "2026-07-31T08:44:00Z" },
  ],
};
