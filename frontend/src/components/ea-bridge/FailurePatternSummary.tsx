import { ArrowDownRight, ArrowUpRight, BarChart3, ExternalLink } from "lucide-react";
import { Link } from "react-router";

const patterns = [
  { id: "counter-trend", label: "Counter-trend entry", losses: 18, share: 42.9, regime: "Strong trend", session: "Asia", delta: 8.4, severity: "CRITICAL" },
  { id: "ranging", label: "Ranging false positive", losses: 13, share: 31, regime: "Ranging", session: "Asia", delta: 3.1, severity: "HIGH" },
  { id: "stale-zone", label: "Mitigated ACR zone", losses: 7, share: 16.7, regime: "Transition", session: "London", delta: -4.2, severity: "MEDIUM" },
  { id: "volatility", label: "ATR expansion entry", losses: 4, share: 9.5, regime: "Breakout", session: "New York", delta: -1.8, severity: "MEDIUM" },
] as const;

const severityTone: Record<(typeof patterns)[number]["severity"], string> = {
  CRITICAL: "bg-rose-500/10 text-rose-500",
  HIGH: "bg-amber-500/10 text-amber-500",
  MEDIUM: "bg-sky-500/10 text-sky-500",
};

export function FailurePatternSummary() {
  return (
    <section aria-label="Trade failure pattern summary" className="rounded-xl border bg-card shadow-sm">
      <header className="flex flex-col justify-between gap-3 border-b p-5 sm:flex-row sm:items-center"><div className="flex items-start gap-3"><span className="rounded-lg bg-primary/10 p-2 text-primary"><BarChart3 className="h-4 w-4" /></span><div><h2 className="font-semibold">Failure pattern summary</h2><p className="mt-0.5 text-xs text-muted-foreground">Aggregated synchronized EA losses from the current 30-day evidence window.</p></div></div><Link to="/diagnostics/patterns" className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline">Full pattern analysis <ExternalLink className="h-3.5 w-3.5" /></Link></header>
      <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-xs"><thead><tr className="border-b text-muted-foreground"><th className="px-5 py-2.5 font-medium">Failure pattern</th><th className="px-3 py-2.5 font-medium">Losses</th><th className="px-3 py-2.5 font-medium">Loss share</th><th className="px-3 py-2.5 font-medium">Dominant regime</th><th className="px-3 py-2.5 font-medium">Session</th><th className="px-3 py-2.5 font-medium">Period delta</th><th className="px-5 py-2.5 text-right font-medium">Severity</th></tr></thead><tbody>{patterns.map((pattern) => { const improving = pattern.delta < 0; const DeltaIcon = improving ? ArrowDownRight : ArrowUpRight; return <tr key={pattern.id} className="border-b last:border-0"><td className="px-5 py-3 font-medium">{pattern.label}</td><td className="px-3 py-3 font-mono">{pattern.losses}</td><td className="px-3 py-3"><div className="flex items-center gap-2"><span className="font-mono">{pattern.share.toFixed(1)}%</span><span className="h-1.5 w-16 overflow-hidden rounded-full bg-muted"><span className="block h-full rounded-full bg-rose-500" style={{ width: `${pattern.share}%` }} /></span></div></td><td className="px-3 py-3">{pattern.regime}</td><td className="px-3 py-3">{pattern.session}</td><td className={`px-3 py-3 font-mono font-semibold ${improving ? "text-emerald-500" : "text-rose-500"}`}><span className="inline-flex items-center gap-1"><DeltaIcon className="h-3.5 w-3.5" /> {pattern.delta > 0 ? "+" : ""}{pattern.delta.toFixed(1)}pp</span></td><td className="px-5 py-3 text-right"><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${severityTone[pattern.severity]}`}>{pattern.severity}</span></td></tr>; })}</tbody></table></div>
      <div className="grid gap-3 border-t p-5 sm:grid-cols-3"><Stat label="Classified losses" value="42 / 44" /><Stat label="Evidence coverage" value="95.5%" /><Stat label="Dominant pattern" value="Counter-trend" /></div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-muted/30 p-3"><p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm font-semibold">{value}</p></div>; }
