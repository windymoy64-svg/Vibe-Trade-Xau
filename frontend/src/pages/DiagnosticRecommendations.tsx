import { ArrowLeft, ArrowUpRight, CheckCircle2, ClipboardCheck, Gauge, Lightbulb, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { PrioritizedRecommendations } from "@/components/diagnostics/PrioritizedRecommendations";
import { LossPatternSummary } from "@/components/diagnostics/LossPatternSummary";
import { diagnosticRecommendationsStub } from "@/data/diagnostic-recommendations";
import { lossPatternAnalysisStub } from "@/data/loss-patterns";

export function DiagnosticRecommendations() {
  const [recommendations, setRecommendations] = useState(diagnosticRecommendationsStub.recommendations);
  const { generatedAt } = diagnosticRecommendationsStub;
  const ready = recommendations.filter((item) => item.status === "READY").length;
  const applied = recommendations.filter((item) => item.status === "APPLIED").length;
  const highPriority = recommendations.filter((item) => item.priority === "CRITICAL" || item.priority === "HIGH").length;
  const projectedImpact = Math.max(...recommendations.map((item) => item.expectedImpact), 0);

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header>
      <Link to="/diagnostics" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Dashboard</Link>
      <div className="mt-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><Sparkles className="h-4 w-4" /> Evidence-based actions <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">Preview data</span></div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Improvement recommendations</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Turn diagnosed loss patterns into prioritized, measurable strategy changes.</p>
        </div>
        <p className="text-xs text-muted-foreground">Generated {new Date(generatedAt).toLocaleString()}</p>
      </div>
    </header>

    <section className="grid gap-3 sm:grid-cols-3">
      <SummaryCard icon={ClipboardCheck} label="Ready to review" value={String(ready)} detail={`${recommendations.length} total recommendations`} />
      <SummaryCard icon={ShieldCheck} label="High priority" value={String(highPriority)} detail="Controls with strongest evidence" tone="text-amber-500" />
      <SummaryCard icon={Gauge} label="Best projected impact" value={`−${projectedImpact}%`} detail="Estimated loss reduction" tone="text-emerald-500" />
    </section>

    <LossPatternSummary analysis={lossPatternAnalysisStub} />

    <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
      <PrioritizedRecommendations recommendations={recommendations} onToggleApplied={(id) => setRecommendations((current) => current.map((item) => item.id === id ? { ...item, status: item.status === "APPLIED" ? "READY" : "APPLIED" } : item))} />
      <aside className="h-fit space-y-4 rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Lightbulb className="h-5 w-5" /></div>
        <div><h2 className="font-semibold">Evidence before optimization</h2><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Apply one controlled change at a time. Measure its result against the linked loss pattern before tuning another parameter.</p></div>
        <div className="rounded-lg bg-emerald-500/5 p-3"><p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Marked as fixed</p><p className="mt-1 text-2xl font-semibold text-emerald-500">{applied}</p><p className="text-xs text-muted-foreground">Mock session state</p></div>
        <div className="space-y-2 border-t pt-4 text-xs text-muted-foreground">
          <p className="flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Review supporting trades</p>
          <p className="flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Define a measurable target</p>
          <p className="flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Validate after deployment</p>
        </div>
        <Link to="/diagnostics/patterns" className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline">Open loss-pattern evidence <ArrowUpRight className="h-3.5 w-3.5" /></Link>
      </aside>
    </section>
  </div>;
}

function SummaryCard({ icon: Icon, label, value, detail, tone = "text-foreground" }: { icon: typeof Gauge; label: string; value: string; detail: string; tone?: string }) {
  return <div className="rounded-xl border bg-card p-5"><div className="flex justify-between text-xs text-muted-foreground"><span>{label}</span><Icon className="h-4 w-4" /></div><p className={`mt-3 text-3xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div>;
}