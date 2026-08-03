import { useState, useEffect } from "react";
import { Activity, Cable, CircleCheck, CircleX, RefreshCcw, Wifi } from "lucide-react";
import type { DataFeedSnapshot } from "@/data/data-feed";
import { dataFeedPreview } from "@/data/data-feed";

export function DataFeedPusher() {
  const [snapshot, setSnapshot] = useState<DataFeedSnapshot>(dataFeedPreview);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Simulate live tick updates every 2 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setSnapshot((current) => {
        if (current.status !== "LIVE") return current;
        const jitter = (Math.random() - 0.5) * 0.15;
        const newPrice = Number((current.latestTick.price + jitter).toFixed(2));
        const updated = {
          ...current,
          latestTick: {
            ...current.latestTick,
            price: newPrice,
            bid: Number((newPrice - 0.05).toFixed(2)),
            ask: Number((newPrice + 0.05).toFixed(2)),
            timestamp: new Date().toISOString(),
          },
          lastUpdateAt: new Date().toISOString(),
          ticksReceived: current.ticksReceived + Math.floor(Math.random() * 3) + 1,
        };
        return updated;
      });
    }, 2000);
    return () => clearInterval(timer);
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setSnapshot(dataFeedPreview);
      setIsRefreshing(false);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Data Feed Pusher</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Real-time OHLC and tick stream monitoring for XAUUSD
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            <RefreshCcw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </header>

        {/* Connection Status Card */}
        <section aria-label="Connection status" className="rounded-xl border bg-card shadow-sm">
          <div className="grid gap-4 p-5 md:grid-cols-[auto_1fr_auto] md:items-center">
            <div className="flex items-center gap-3">
              <span
                className={`rounded-lg p-2 ${
                  snapshot.status === "LIVE"
                    ? "bg-emerald-500/10 text-emerald-500"
                    : snapshot.status === "OFFLINE"
                      ? "bg-rose-500/10 text-rose-500"
                      : "bg-amber-500/10 text-amber-500"
                }`}
              >
                {snapshot.status === "LIVE" ? (
                  <Wifi className="h-5 w-5" />
                ) : snapshot.status === "OFFLINE" ? (
                  <CircleX className="h-5 w-5" />
                ) : (
                  <Activity className="h-5 w-5" />
                )}
              </span>
              <div>
                <h2 className="font-semibold">MT5 Terminal A · {snapshot.symbol}</h2>
                <p className="text-xs text-muted-foreground">{snapshot.connectionInfo.source}</p>
              </div>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Status connection</p>
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold`}>
                {snapshot.status === "LIVE" ? (
                  <CircleCheck className="h-3.5 w-3.5" />
                ) : (
                  <Activity className="h-3.5 w-3.5" />
                )}
                {snapshot.status} · Uptime {Math.floor(snapshot.connectionInfo.uptimeSeconds / 3600)}h{" "}
                {Math.floor((snapshot.connectionInfo.uptimeSeconds % 3600) / 60)}m
              </span>
            </div>
            <div className="text-right text-xs text-muted-foreground">
              Latency average: {snapshot.avgLatencyMs}ms
            </div>
          </div>
        </section>

        {/* Live Price & Tick Counter */}
        <section aria-label="Live market data" className="rounded-xl border bg-card shadow-sm">
          <div className="grid gap-4 p-5 md:grid-cols-3">
            <MetricCard label="Latest Price" value={snapshot.latestTick.price.toFixed(2)} suffix=" USD" />
            <MetricCard label="Spread" value={(snapshot.latestTick.ask - snapshot.latestTick.bid).toFixed(2)} suffix=" USD" />
            <MetricCard label="Ticked" value={snapshot.ticksReceived.toLocaleString()} suffix=" total" />
          </div>
        </section>

        {/* OHLC Bars Table */}
        <section aria-label="Recent OHLC bars" className="rounded-xl border bg-card shadow-sm">
          <div className="border-b p-5">
            <h2 className="font-semibold">Recent OHLC Bars (M1)</h2>
            <p className="text-xs text-muted-foreground">Last 5 completed 1-minute candles</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-left text-xs">
              <thead className="bg-muted/30 text-muted-foreground">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Time</th>
                  <th className="px-4 py-2.5 font-medium">Open</th>
                  <th className="px-4 py-2.5 font-medium">High</th>
                  <th className="px-4 py-2.5 font-medium">Low</th>
                  <th className="px-4 py-2.5 font-medium">Close</th>
                  <th className="px-4 py-2.5 font-medium">Volume</th>
                </tr>
              </thead>
              <tbody>
                {snapshot.recentBars.map((bar, idx) => (
                  <tr key={idx} className="border-b last:border-0">
                    <td className="px-4 py-3 font-mono">
                      {new Date(bar.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </td>
                    <td className="px-4 py-3 font-mono">{bar.open.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-emerald-500">{bar.high.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-rose-500">{bar.low.toFixed(2)}</td>
                    <td className={`px-4 py-3 font-mono font-semibold ${bar.close >= bar.open ? "text-emerald-500" : "text-rose-500"}`}>
                      {bar.close.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 font-mono">{bar.volume.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Summary Stats */}
        <section aria-label="Stream statistics" className="rounded-xl border bg-card shadow-sm">
          <div className="grid gap-4 p-5 md:grid-cols-4">
            <SummaryStat label="Total Bars" value={snapshot.barsReceived.toLocaleString()} />
            <SummaryStat label="Total Ticks" value={snapshot.ticksReceived.toLocaleString()} />
            <SummaryStat label="Avg Latency" value={`${snapshot.avgLatencyMs} ms`} />
            <SummaryStat label="Last Update" value={new Date(snapshot.lastUpdateAt).toLocaleTimeString()} />
          </div>
        </section>

        {/* Disclaimer */}
        <footer className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-xs text-muted-foreground">
          <div className="flex items-start gap-2">
            <Cable className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
            <p>Preview only — no live MT5 connection established. Data is simulated for demonstration purposes.</p>
          </div>
        </footer>
      </div>
    </div>
  );
}

function MetricCard({ label, value, suffix }: { label: string; value: string; suffix?: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">
        {value}{suffix}
      </p>
    </div>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-background/70 p-3">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-sm font-semibold">{value}</p>
    </div>
  );
}
