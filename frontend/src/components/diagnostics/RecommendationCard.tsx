import { ArrowUpRight, Check, RotateCcw, Target } from "lucide-react";
import { Link } from "react-router";
import type { DiagnosticRecommendation, RecommendationPriority } from "@/data/diagnostic-recommendations";
import { RecommendationSteps } from "@/components/diagnostics/RecommendationSteps";

function priorityClass(priority: RecommendationPriority): string {
  if (priority === "CRITICAL") return "bg-rose-500/10 text-rose-500";
  if (priority === "HIGH") return "bg-amber-500/10 text-amber-500";
  return "bg-sky-500/10 text-sky-500";
}

export function RecommendationCard({ recommendation, rank, onToggleApplied }: { recommendation: DiagnosticRecommendation; rank: number; onToggleApplied?: (id: string) => void }) {
  const applied = recommendation.status === "APPLIED";
  return <article className={`rounded-xl border bg-card p-5 shadow-sm ${applied ? "border-emerald-500/30" : ""}`}>
    <div className="flex items-start gap-4">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 font-mono text-sm font-semibold text-primary">{rank}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold">{recommendation.title}</h2>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${priorityClass(recommendation.priority)}`}>{recommendation.priority}</span>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${applied ? "bg-emerald-500/10 text-emerald-500" : "bg-muted text-muted-foreground"}`}>{recommendation.status}</span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{recommendation.summary}</p>
        <div className="mt-4 rounded-lg border-l-2 border-primary bg-primary/5 p-3 text-sm"><span className="font-medium">Recommended action:</span> <span className="text-muted-foreground">{recommendation.action}</span></div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Expected impact" value={`−${recommendation.expectedImpact}% loss`} tone="text-emerald-500" />
          <Metric label="Evidence" value={`${recommendation.evidenceLosses} losses`} />
          <Metric label="Confidence" value={`${recommendation.confidence}%`} />
          <Metric label="Effort" value={recommendation.effort} />
        </div>
        <RecommendationSteps recommendation={recommendation} />
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t pt-3">
          <Link to={`/diagnostics/trades?reason=${encodeURIComponent(recommendation.patternName)}`} className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"><Target className="h-3.5 w-3.5" /> Evidence: {recommendation.patternName}</Link>
          <div className="flex flex-wrap items-center gap-2">
            <Link to={`/diagnostics/recommendations/${recommendation.id}`} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">Review recommendation <ArrowUpRight className="h-3.5 w-3.5" /></Link>
            {onToggleApplied && <button type="button" onClick={() => onToggleApplied(recommendation.id)} className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium ${applied ? "border bg-card text-muted-foreground hover:bg-muted" : "bg-emerald-600 text-white hover:bg-emerald-700"}`}>{applied ? <RotateCcw className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}{applied ? "Reopen" : "Mark as fixed"}</button>}
          </div>
        </div>
      </div>
    </div>
  </article>;
}

function Metric({ label, value, tone = "text-foreground" }: { label: string; value: string; tone?: string }) {
  return <div><p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-sm font-semibold ${tone}`}>{value}</p></div>;
}