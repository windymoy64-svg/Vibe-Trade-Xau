// Mock data type definitions for Data Feed Pusher features
export interface OHLCBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TickData {
  timestamp: string;
  price: number;
  bid: number;
  ask: number;
  volume: number;
}

export interface DataFeedSnapshot {
  id: string;
  symbol: string;
  status: "LIVE" | "OFFLINE" | "RECONNECTING";
  lastUpdateAt: string;
  barsReceived: number;
  ticksReceived: number;
  avgLatencyMs: number;
  recentBars: OHLCBar[];
  latestTick: TickData;
  connectionInfo: {
    source: string;
    endpoint?: string;
    uptimeSeconds: number;
  };
}

// Generate realistic mock OHLC bar data
function generateOHLCBar(basePrice: number, index: number): OHLCBar {
  const time = new Date(Date.now() - (59 - index) * 60_000);
  const change = (Math.random() - 0.5) * 2; // small random move
  const open = basePrice + Math.random() * 0.5 - 0.25;
  const high = Math.max(open, open + Math.random());
  const low = Math.min(open, open - Math.random());
  const close = open + change;
  return {
    timestamp: time.toISOString(),
    open: Number(open.toFixed(2)),
    high: Number(high.toFixed(2)),
    low: Number(low.toFixed(2)),
    close: Number(close.toFixed(2)),
    volume: Math.floor(Math.random() * 1000) + 100,
  };
}

// Generate realistic tick data
function generateTick(basePrice: number): TickData {
  const time = new Date().toISOString();
  const jitter = (Math.random() - 0.5) * 0.1;
  const bid = basePrice + jitter - 0.05;
  const ask = bid + 0.1;
  return {
    timestamp: time,
    price: Number((bid + 0.05).toFixed(2)),
    bid: Number(bid.toFixed(2)),
    ask: Number(ask.toFixed(2)),
    volume: Math.floor(Math.random() * 50) + 10,
  };
}

// Main snapshot with live simulation state
export function generateDataFeedSnapshot(): DataFeedSnapshot {
  const basePrice = 2389.50;
  const bars: OHLCBar[] = Array.from({ length: 20 }, (_, i) => generateOHLCBar(basePrice, i));

  return {
    id: "feed-xauusd-live",
    symbol: "XAUUSD",
    status: "LIVE",
    lastUpdateAt: new Date().toISOString(),
    barsReceived: 1247,
    ticksReceived: 8934,
    avgLatencyMs: 42,
    recentBars: bars.slice(-5),
    latestTick: generateTick(basePrice),
    connectionInfo: {
      source: "MT5 Terminal A",
      endpoint: "http://127.0.0.1:443",
      uptimeSeconds: 14523,
    },
  };
}

// Export single instance for import elsewhere
export const dataFeedPreview = generateDataFeedSnapshot();
