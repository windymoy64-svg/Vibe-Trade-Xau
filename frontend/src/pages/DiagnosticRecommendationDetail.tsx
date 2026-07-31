import { ArrowLeft, Check, Gauge, RotateCcw, ShieldAlert, Target } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { RecommendationSteps } from "@/components/diagnostics/RecommendationSteps";
import { diagnosticRecommendationsStub } from "@/data/diagnostic-recommendations";

export function DiagnosticRecommendationDetail() {
  const { recommendationId } = useParams();
  const source = diagnosticRecommendationsStub.recommendations.find((item) => item.id === recommendationId);
  const [applied, setApplied] = useState(source?.status === "APPLIED");

  if (!source) {
    return <div className="mx-auto max-w-3xl p-6 lg:p-8"><Link to="/diagnostics/recommendations" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Recommendations</Link><div className="mt-8 rounded-xl border border-dashed bg-card p-10 text-center"><h1 className="font-semibold">Recommendation not found</h1><p className="mt-1 text-sm text-muted-foreground">The requested recommendation is unavailable in the current diagnostic data.</p></div></div>;
  }

  const recommendation = { ...source, status: applied ? "APPLIED" as const : source.status === "APPLIED" ? "READY" as const : source.status };

  return <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header>
      <Link to="/diagnostics/recommendations" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Recommendations</Link>
      <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div><div className="flex flex-wrap gap-2"><span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">{recommendation.priority}</span><span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${applied ? "bg-emerald-500/10 text-emerald-500" : "bg-muted text-muted-foreground"}`}>{recommendation.status}</span></div><h1 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">{recommendation.title}</h1><p className="mt-2 max-w-2xl text-sm text-muted-foreground">{recommendation.summary}</p></div>
        <button type="button" onClick={() => setApplied((value) => !value)} className={`inline-flex w-fit items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${applied ? "border bg-card text-muted-foreground hover:bg-muted" : "bg-emerald-600 text-white hover:bg-emerald-700"}`}>{applied ? <RotateCcw className="h-4 w-4" /> : <Check className="h-4 w-4" />}{applied ? "Reopen recommendation" : "Mark as fixed"}</button>
      </div>
    </header>

    <section className="grid gap-3 sm:grid-cols-4">
      <Metric label="Expected impact" value={`−${recommendation.expectedImpact}%`} icon={Gauge} tone="text-emerald-500" />
      <Metric label="Evidence" value={`${recommendation.evidenceLosses} losses`} icon={Target} />
      <Metric label="Confidence" value={`${recommendation.confidence}%`} icon={Gauge} />
      <Metric label="Effort" value={recommendation.effort} icon={ShieldAlert} />
    </section>

    <section className="rounded-xl border bg-card p-5 shadow-sm"><h2 className="font-semibold">Recommended strategy change</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{recommendation.action}</p><RecommendationSteps recommendation={recommendation} /></section>

    <section className="grid gap-4 sm:grid-cols-2">
      <div className="rounded-xl border bg-card p-5"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Linked diagnostic pattern</p><h2 className="mt-2 font-semibold">{recommendation.patternName}</h2><p className="mt-1 text-sm text-muted-foreground">This recommendation is supported by {recommendation.evidenceLosses} classified losses.</p><Link to={`/diagnostics/trades?reason=${encodeURIComponent(recommendation.patternName)}`} className="mt-4 inline-flex text-xs font-medium text-primary hover:underline">Review supporting trades</Link></div>
      <div className="rounded-xl border bg-card p-5"><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Implementation discipline</p><h2 className="mt-2 font-semibold">Change one control at a time</h2><p className="mt-1 text-sm text-muted-foreground">Validate against the target before combining this recommendation with another strategy modification.</p><Link to="/diagnostics/patterns" className="mt-4 inline-flex text-xs font-medium text-primary hover:underline">Open pattern analysis</Link></div>
    </section>
  </div>;
}

function Metric({ label, value, icon: Icon, tone = "text-foreground" }: { label: string; value: string; icon: typeof Gauge; tone?: string }) {
  return <div className="rounded-xl border bg-card p-4"><div className="flex justify-between text-[10px] uppercase text-muted-foreground"><span>{label}</span><Icon className="h-3.5 w-3.5" /></div><p className={`mt-2 font-mono text-lg font-semibold ${tone}`}>{value}</p></div>;
}