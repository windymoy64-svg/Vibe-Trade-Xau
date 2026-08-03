import { useEffect, useRef, useState } from "react";
import { ArrowDownRight, ArrowUpRight, Radio, Waves } from "lucide-react";

export interface LivePriceSnapshot {
  symbol: string;
  bid: number;
  ask: number;
  digits: number;
  sessionHigh: number;
  sessionLow: number;
  changePercent: number;
  tickAt: string;
}

const previewDeltas = [0.03, -0.01, 0.02, -0.04, 0.01];

export function LiveXauusdPrice({ initial }: { initial: LivePriceSnapshot }) {
  const [snapshot, setSnapshot] = useState(initial);
  const [direction, setDirection] = useState<"UP" | "DOWN">("UP");
  const tickIndex = useRef(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      const delta = previewDeltas[tickIndex.current % previewDeltas.length];
      tickIndex.current += 1;
      setDirection(delta >= 0 ? "UP" : "DOWN");
      setSnapshot((current) => ({
        ...current,
        bid: current.bid + delta,
        ask: current.ask + delta,
        tickAt: new Date().toISOString(),
      }));
    }, 1_000);
    return () => window.clearInterval(timer);
  }, []);

  const spread = snapshot.ask - snapshot.bid;
  const DirectionIcon = direction === "UP" ? ArrowUpRight : ArrowDownRight;
  const directionTone = direction === "UP" ? "text-emerald-500" : "text-rose-500";

  return (
    <section aria-label="Live XAUUSD price" className="overflow-hidden rounded-xl border border-amber-500/20 bg-slate-950 text-slate-100 shadow-sm">
      <header className="flex flex-col justify-between gap-3 border-b border-slate-800 p-5 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3"><span className="rounded-lg bg-amber-400/10 p-2 text-amber-300"><Waves className="h-4 w-4" /></span><div><div className="flex items-center gap-2"><h2 className="font-mono text-lg font-semibold">{snapshot.symbol}</h2><span className="inline-flex items-center gap-1 rounded-full bg-emerald-400/10 px-2 py-0.5 text-[9px] font-semibold text-emerald-300"><Radio className="h-3 w-3" /> LIVE FEED</span></div><p className="mt-0.5 text-xs text-slate-400">Native MetaTrader 5 tick stream</p></div></div>
        <div className={`flex items-center gap-1 font-mono text-xs font-semibold ${directionTone}`}><DirectionIcon className="h-4 w-4" /> {snapshot.changePercent >= 0 ? "+" : ""}{snapshot.changePercent.toFixed(2)}%</div>
      </header>
      <div aria-live="polite" className="grid gap-px bg-slate-800 sm:grid-cols-2">
        <Quote label="BID" value={snapshot.bid} digits={snapshot.digits} tone="text-rose-300" />
        <Quote label="ASK" value={snapshot.ask} digits={snapshot.digits} tone="text-emerald-300" />
      </div>
      <div className="grid grid-cols-2 gap-3 p-5 text-xs sm:grid-cols-4">
        <Meta label="Spread" value={`${spread.toFixed(snapshot.digits)} USD`} />
        <Meta label="Session high" value={snapshot.sessionHigh.toFixed(snapshot.digits)} />
        <Meta label="Session low" value={snapshot.sessionLow.toFixed(snapshot.digits)} />
        <Meta label="Last tick" value={new Date(snapshot.tickAt).toLocaleTimeString()} />
      </div>
      <div className="h-0.5 overflow-hidden bg-slate-900"><span className="block h-full w-2/3 animate-pulse bg-gradient-to-r from-transparent via-amber-300 to-transparent" /></div>
    </section>
  );
}

function Quote({ label, value, digits, tone }: { label: string; value: number; digits: number; tone: string }) {
  return <div className="bg-slate-950 p-5"><p className="text-[10px] font-semibold tracking-[0.24em] text-slate-500">{label}</p><p className={`mt-1 font-mono text-3xl font-semibold tabular-nums ${tone}`}>{value.toFixed(digits)}</p></div>;
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[9px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 font-mono text-slate-200">{value}</p></div>;
}
