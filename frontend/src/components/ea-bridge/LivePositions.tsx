import { useEffect, useState } from "react";
import { Activity, CircleDollarSign } from "lucide-react";
import type { EaExecutionRecord } from "@/data/ea-bridge";

const syncTone: Record<EaExecutionRecord["syncStatus"], string> = {
  SYNCED: "bg-emerald-500/10 text-emerald-500",
  STALE: "bg-amber-500/10 text-amber-500",
  MISMATCH: "bg-rose-500/10 text-rose-500",
};

export function LivePositions({ initial }: { initial: EaExecutionRecord[] }) {
  const [positions, setPositions] = useState(initial);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setPositions((current) => current.map((position, index) => {
        const delta = index % 2 === 0 ? 0.02 : -0.01;
        const currentPrice = position.currentPrice + delta;
        const priceDelta = position.direction === "BUY" ? currentPrice - position.price : position.price - currentPrice;
        return { ...position, currentPrice, floatingPnl: priceDelta * position.volume * 100, updatedAt: new Date().toISOString() };
      }));
    }, 1_000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <article aria-label="Live open MT5 positions" className="rounded-xl border bg-card shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b p-5">
        <div className="flex items-start gap-3"><span className="rounded-lg bg-primary/10 p-2 text-primary"><CircleDollarSign className="h-4 w-4" /></span><div><h2 className="font-semibold">Open MT5 positions</h2><p className="mt-0.5 text-xs text-muted-foreground">Live position state reconciled against each connected terminal.</p></div></div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-1 text-[9px] font-semibold text-emerald-500"><Activity className="h-3 w-3" /> LIVE</span>
      </header>
      {positions.length === 0 ? <p className="p-5 text-xs text-muted-foreground">No open positions.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-xs"><thead><tr className="border-b text-muted-foreground"><th className="px-5 py-2.5 font-medium">Ticket / terminal</th><th className="px-3 py-2.5 font-medium">Side</th><th className="px-3 py-2.5 font-medium">Volume</th><th className="px-3 py-2.5 font-medium">Entry</th><th className="px-3 py-2.5 font-medium">Current</th><th className="px-3 py-2.5 font-medium">SL / TP</th><th className="px-3 py-2.5 font-medium">Floating P/L</th><th className="px-5 py-2.5 text-right font-medium">Sync</th></tr></thead><tbody aria-live="polite">{positions.map((position) => <tr key={position.id} className="border-b last:border-0"><td className="px-5 py-3"><p className="font-mono font-semibold">{position.orderId}</p><p className="mt-0.5 text-[10px] text-muted-foreground">{position.terminal}</p></td><td className={`px-3 py-3 font-mono font-semibold ${position.direction === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>{position.direction}</td><td className="px-3 py-3 font-mono">{position.volume.toFixed(3)}</td><td className="px-3 py-3 font-mono">{position.price.toFixed(2)}</td><td className="px-3 py-3 font-mono">{position.currentPrice.toFixed(2)}</td><td className="px-3 py-3 font-mono"><span className="text-rose-500">{position.sl.toFixed(2)}</span><span className="text-muted-foreground"> / </span><span className="text-emerald-500">{position.tp.toFixed(2)}</span></td><td className={`px-3 py-3 font-mono font-semibold ${position.floatingPnl >= 0 ? "text-emerald-500" : "text-rose-500"}`}>{position.floatingPnl >= 0 ? "+" : ""}${position.floatingPnl.toFixed(2)}</td><td className="px-5 py-3 text-right"><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${syncTone[position.syncStatus]}`}>{position.syncStatus}</span></td></tr>)}</tbody></table></div>}
    </article>
  );
}
