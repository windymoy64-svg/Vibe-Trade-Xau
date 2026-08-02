import { Crosshair, MoveDown } from "lucide-react";
import type { PrecisionEntryPreview } from "@/data/precision-execution";

export function PrecisionEntryPrice({ entry }: { entry: PrecisionEntryPreview }) {
  const distance = Math.abs(entry.currentPrice - entry.price);
  return <article className="overflow-hidden rounded-xl border border-emerald-500/30 bg-slate-950 text-slate-100 shadow-sm" aria-label="Precise entry price">
    <div className="flex flex-col justify-between gap-4 border-b border-slate-800 p-5 sm:flex-row sm:items-start"><div><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-400"><Crosshair className="h-4 w-4" /> Precision entry</div><p className="mt-2 text-sm text-slate-400">{entry.symbol} · {entry.direction} LIMIT</p></div><span className="self-start rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-400">5-decimal quote</span></div>
    <div className="grid gap-5 p-5 lg:grid-cols-[minmax(260px,0.85fr)_minmax(0,1.15fr)]"><div><p className="text-[10px] uppercase tracking-wider text-slate-500">Exact entry price</p><p className="mt-2 font-mono text-4xl font-bold tracking-tight text-emerald-400 sm:text-5xl">{entry.price.toFixed(5)}</p><div className="mt-3 flex items-center gap-2 text-xs text-slate-400"><MoveDown className="h-3.5 w-3.5 text-amber-400" /> {distance.toFixed(5)} below current price</div></div><div className="grid grid-cols-2 gap-3"><Metric label="Zone low" value={entry.zoneLow} /><Metric label="Zone high" value={entry.zoneHigh} /><Metric label="Current price" value={entry.currentPrice} /><Metric label="Tick size" value={entry.tickSize} /><div className="col-span-2 rounded-lg border border-slate-800 bg-slate-900/70 p-3"><p className="text-[9px] uppercase tracking-wider text-slate-500">Calculation source</p><p className="mt-1 text-xs text-slate-300">{entry.source}</p></div></div></div>
  </article>;
}

function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3"><p className="text-[9px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 font-mono text-sm font-semibold text-slate-200">{value.toFixed(5)}</p></div>; }
