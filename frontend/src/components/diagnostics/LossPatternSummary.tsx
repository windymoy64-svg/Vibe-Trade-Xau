import { ArrowDownRight, ArrowUpRight, BrainCircuit } from "lucide-react";
import { Link } from "react-router";
import type { LossPatternAnalysisData } from "@/data/loss-patterns";

export function LossPatternSummary({ analysis }: { analysis: LossPatternAnalysisData }) {
  const dominantPatterns = [...analysis.patterns]
    .sort((left, right) => right.lossPercentage - left.lossPercentage)
    .slice(0, 3);

  return <section className="rounded-xl border bg-card p-5 shadow-sm">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><div className="flex items-center gap-2"><BrainCircuit className="h-4 w-4 text-primary" /><h2 className="font-semibold">Diagnostic pattern summary</h2></div><p className="mt-1 text-xs text-muted-foreground">The strongest evidence driving these recommendations</p></div>
      <Link to="/diagnostics/patterns" className="text-xs font-medium text-primary hover:underline">View full analysis</Link>
    </div>
    {dominantPatterns.length === 0 ? <p className="mt-5 rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground">No diagnosed loss patterns are available.</p> : <div className="mt-4 grid gap-3 sm:grid-cols-3">
      {dominantPatterns.map((pattern, index) => {
        const delta = pattern.trendDelta ?? 0;
        return <article key={pattern.id} className="rounded-lg border bg-background/50 p-3">
          <div className="flex items-center justify-between gap-2"><span className="font-mono text-[10px] text-muted-foreground">#{index + 1}</span><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${pattern.severity === "HIGH" ? "bg-rose-500/10 text-rose-500" : pattern.severity === "MEDIUM" ? "bg-amber-500/10 text-amber-500" : "bg-sky-500/10 text-sky-500"}`}>{pattern.severity}</span></div>
          <h3 className="mt-2 text-sm font-medium">{pattern.name}</h3>
          <div className="mt-3 flex items-end justify-between"><div><p className="text-[10px] uppercase text-muted-foreground">Loss share</p><p className="font-mono text-xl font-semibold">{pattern.lossPercentage}%</p></div><span className={`inline-flex items-center gap-1 text-xs font-medium ${delta <= 0 ? "text-emerald-500" : "text-rose-500"}`}>{delta <= 0 ? <ArrowDownRight className="h-3.5 w-3.5" /> : <ArrowUpRight className="h-3.5 w-3.5" />}{delta > 0 ? "+" : ""}{delta} pp</span></div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(pattern.lossPercentage, 100)}%` }} /></div>
        </article>;
      })}
    </div>}
    <p className="mt-4 text-xs text-muted-foreground"><strong className="text-foreground">{analysis.insight.title}:</strong> {analysis.insight.detail}</p>
  </section>;
}