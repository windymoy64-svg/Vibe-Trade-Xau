import { ArrowDownRight, ArrowUpRight, BrainCircuit, Lightbulb } from "lucide-react";
import { Link } from "react-router";

const patterns = [
  { id: "counter-trend", label: "Counter-trend entry", share: 42.9, losses: 18, confidence: 94, delta: 8.4, insight: "Strong HTF bias contradicted the execution direction." },
  { id: "ranging", label: "Ranging false positive", share: 31, losses: 13, confidence: 91, delta: 3.1, insight: "Trend filters accepted low-expansion market structure." },
  { id: "asia", label: "Asia session liquidity", share: 19, losses: 8, confidence: 86, delta: -2.7, insight: "Thin liquidity increased false breakout frequency." },
] as const;

export function Mt5FailurePatternSummary() {
  return (
    <section aria-label="MT5 failure pattern summary" className="rounded-xl border bg-card shadow-sm">
      <header className="flex flex-col justify-between gap-3 border-b p-5 sm:flex-row sm:items-center"><div className="flex items-start gap-3"><span className="rounded-lg bg-primary/10 p-2 text-primary"><BrainCircuit className="h-4 w-4" /></span><div><h2 className="font-semibold">Production failure patterns</h2><p className="mt-0.5 text-xs text-muted-foreground">Dominant causes classified from broker-native MT5 executions.</p></div></div><Link to="/diagnostics/patterns" className="text-xs font-medium text-primary hover:underline">Open pattern workspace</Link></header>
      <div className="grid gap-4 p-5 lg:grid-cols-3">{patterns.map((pattern, index) => { const improving = pattern.delta < 0; const DeltaIcon = improving ? ArrowDownRight : ArrowUpRight; return <article key={pattern.id} className={`rounded-xl border p-4 ${index === 0 ? "border-rose-500/30 bg-rose-500/5" : "bg-muted/20"}`}><div className="flex items-start justify-between gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-background font-mono text-xs font-semibold">{index + 1}</span><span className={`inline-flex items-center gap-1 font-mono text-xs font-semibold ${improving ? "text-emerald-500" : "text-rose-500"}`}><DeltaIcon className="h-3.5 w-3.5" /> {pattern.delta > 0 ? "+" : ""}{pattern.delta.toFixed(1)}pp</span></div><h3 className="mt-4 text-sm font-semibold">{pattern.label}</h3><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{pattern.insight}</p><div className="mt-4 grid grid-cols-3 gap-2"><Stat label="Losses" value={String(pattern.losses)} /><Stat label="Share" value={`${pattern.share.toFixed(1)}%`} /><Stat label="Confidence" value={`${pattern.confidence}%`} /></div></article>; })}</div>
      <div className="border-t p-5"><div className="flex gap-3 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4"><Lightbulb className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" /><div><p className="text-xs font-semibold">Highest-impact next action</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Require HTF direction agreement before execution and block new entries while the MT5 regime snapshot remains ranging. This targets 73.9% of classified losses without changing RSI parameters.</p></div></div></div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-background/70 p-2"><p className="text-[8px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-xs font-semibold">{value}</p></div>; }
