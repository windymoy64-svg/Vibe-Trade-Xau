import { useState, useEffect } from "react";
import { Activity, Play, Pause, RefreshCw, TrendingUp, TrendingDown, Clock } from "lucide-react";

interface OHLCBar {
  id: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const mockOHLCData: OHLCBar[] = [
  { id: "bar-1", timestamp: "2026-08-04T14:30:00Z", open: 2345.00, high: 2347.50, low: 2344.00, close: 2346.20, volume: 1250 },
  { id: "bar-2", timestamp: "2026-08-04T14:35:00Z", open: 2346.20, high: 2349.00, low: 2345.50, close: 2348.50, volume: 1380 },
  { id: "bar-3", timestamp: "2026-08-04T14:40:00Z", open: 2348.50, high: 2350.00, low: 2347.00, close: 2349.80, volume: 1520 },
  { id: "bar-4", timestamp: "2026-08-04T14:45:00Z", open: 2349.80, high: 2352.00, low: 2349.00, close: 2351.20, volume: 1650 },
  { id: "bar-5", timestamp: "2026-08-04T14:50:00Z", open: 2351.20, high: 2353.50, low: 2350.50, close: 2352.80, volume: 1420 },
  { id: "bar-6", timestamp: "2026-08-04T14:55:00Z", open: 2352.80, high: 2354.00, low: 2351.00, close: 2353.20, volume: 1350 },
  { id: "bar-7", timestamp: "2026-08-04T15:00:00Z", open: 2353.20, high: 2355.00, low: 2352.50, close: 2354.50, volume: 1480 },
  { id: "bar-8", timestamp: "2026-08-04T15:05:00Z", open: 2354.50, high: 2356.00, low: 2353.00, close: 2355.80, volume: 1590 },
  { id: "bar-9", timestamp: "2026-08-04T15:10:00Z", open: 2355.80, high: 2357.50, low: 2354.00, close: 2356.20, volume: 1420 },
  { id: "bar-10", timestamp: "2026-08-04T15:15:00Z", open: 2356.20, high: 2358.00, low: 2355.50, close: 2357.00, volume: 1680 },
];

export function LiveOHLC() {
  const [data, setData] = useState<OHLCBar[]>(mockOHLCData);
  const [isStreaming, setIsStreaming] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const currentPrice = data[data.length - 1].close;
  const previousClose = data[data.length - 2]?.close || currentPrice;
  const priceChange = currentPrice - previousClose;
  const percentChange = (priceChange / previousClose) * 100;

  useEffect(() => {
    if (!isStreaming) return;

    const interval = setInterval(() => {
      const lastBar = data[data.length - 1];
      const newPrice = lastBar.close + (Math.random() - 0.45) * 1.5;
      
      setData((prev) => {
        const updatedBar = {
          ...prev[prev.length - 1],
          high: Math.max(prev[prev.length - 1].high, newPrice),
          low: Math.min(prev[prev.length - 1].low, newPrice),
          close: newPrice,
        };
        return [...prev.slice(0, -1), updatedBar];
      });

      setLastUpdate(new Date());
    }, 3000);

    return () => clearInterval(interval);
  }, [isStreaming, data]);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
      <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary">
            <Activity className="h-4 w-4" />
            Live OHLC Stream
            <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] tracking-normal text-emerald-500">Live</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Real-time Market Data Feed</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Monitor live OHLC (Open, High, Low, Close) bars for XAUUSD with millisecond precision updates.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setIsStreaming(!isStreaming)}
            className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${
              isStreaming ? "bg-amber-500 text-white hover:bg-amber-500/90" : "bg-emerald-500 text-white hover:bg-emerald-500/90"
            }`}
          >
            {isStreaming ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            {isStreaming ? "Pause" : "Resume"}
          </button>
          <button
            onClick={() => setData(mockOHLCData)}
            className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Reset
          </button>
        </div>
      </header>

      {/* Current Price Display */}
      <section className="rounded-xl border bg-card p-6 shadow-sm">
        <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
          <div className="text-center md:text-left">
            <p className="text-xs uppercase tracking-wider text-muted-foreground">XAUUSD Current Price</p>
            <div className="mt-2 flex items-baseline justify-center gap-2 md:justify-start">
              <h2 className="text-4xl font-mono font-bold tracking-tight">${currentPrice.toFixed(2)}</h2>
              <span
                className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-bold ${
                  priceChange >= 0 ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                }`}
              >
                {priceChange >= 0 ? <TrendingUp className="mr-1 h-3.5 w-3.5" /> : <TrendingDown className="mr-1 h-3.5 w-3.5" />}
                {priceChange >= 0 ? "+" : ""}{priceChange.toFixed(2)} ({percentChange.toFixed(2)}%)
              </span>
            </div>
            <div className="mt-2 flex items-center justify-center gap-2 text-xs text-muted-foreground md:justify-start">
              <Clock className="h-3.5 w-3.5" />
              <span>Last update: {lastUpdate.toLocaleTimeString()}</span>
              {isStreaming && <span className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500"></span> Streaming</span>}
            </div>
          </div>

          {/* Mini Chart Visualization */}
          <div className="flex items-center gap-1">
            {data.slice(-10).map((bar, index) => (
              <div key={index} className="group relative h-16 w-4">
                <div
                  className={`absolute left-1/2 top-0 mx-auto h-full w-1 rounded-full ${
                    bar.close >= bar.open ? "bg-emerald-500" : "bg-rose-500"
                  }`}
                  style={{ 
                    height: `${((bar.high - bar.low) / 10) * 100}%`,
                    top: `${100 - ((bar.high - bar.low) / 10) * 100 - ((bar.low - 2340) / 10) * 100}%`
                  }}
                />
                <div
                  className="absolute top-1/2 -translate-y-1/2 h-1.5 w-3 rounded-sm"
                  style={{
                    left: `calc(50% - ${(bar.open - bar.close) * 5}px)`,
                    backgroundColor: bar.close >= bar.open ? "#10b981" : "#f43f5e"
                  }}
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* OHLC Bars Grid */}
      <article className="rounded-xl border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b p-5">
          <div>
            <h2 className="font-semibold">Recent OHLC Bars</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">5-minute intervals • Auto-refreshing</p>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <p>Total bars: {data.length}</p>
            <p className="text-[10px]">Showing latest 10</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-4 py-3 font-medium">Time</th>
                <th className="px-4 py-3 font-medium text-right">Open</th>
                <th className="px-4 py-3 font-medium text-right text-emerald-500">High</th>
                <th className="px-4 py-3 font-medium text-right text-rose-500">Low</th>
                <th className="px-4 py-3 font-medium text-right">Close</th>
                <th className="px-4 py-3 font-medium text-right">Change</th>
                <th className="px-4 py-3 font-medium text-right">Volume</th>
              </tr>
            </thead>
            <tbody>
              {data.map((bar) => {
                const change = bar.close - bar.open;
                return (
                  <tr key={bar.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 text-muted-foreground">{new Date(bar.timestamp).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-mono">${bar.open.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-mono text-emerald-500 font-semibold">${bar.high.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-mono text-rose-500 font-semibold">${bar.low.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-mono">${bar.close.toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right font-mono font-semibold ${change >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                      {change >= 0 ? "+" : ""}{change.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono">{bar.volume}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </article>

      {/* Stats Summary */}
      <section className="grid gap-3 sm:grid-cols-3">
        <Metric label="Session Open" value={data[0].open.toFixed(2)} detail={`${data.length} bars captured`} />
        <Metric label="Session High" value={data.reduce((max, b) => Math.max(max, b.high), 0).toFixed(2)} detail="Peak price today" />
        <Metric label="Session Low" value={data.reduce((min, b) => Math.min(min, b.low), Infinity).toFixed(2)} detail="Floor price today" />
      </section>

      {/* Info Banner */}
      <div className="rounded-xl border bg-sky-500/5 p-4">
        <div className="flex items-start gap-2">
          <svg className="h-4 w-4 text-sky-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-xs text-sky-700">
            <p className="font-medium">Data Source</p>
            <p className="mt-1">
              This demo displays simulated OHLC data for development purposes. In production, this stream connects to real market feeds via WebSocket.
              All prices are generated randomly around the current market rate for testing UI components.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-xl font-semibold">${value}</p>
      {detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}
    </div>
  );
}
