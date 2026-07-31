import { CheckCircle2, ChevronDown, ShieldAlert, Target } from "lucide-react";
import { useState } from "react";
import type { DiagnosticRecommendation } from "@/data/diagnostic-recommendations";

export function RecommendationSteps({ recommendation }: { recommendation: DiagnosticRecommendation }) {
  const [open, setOpen] = useState(false);

  return <div className="mt-4 overflow-hidden rounded-lg border bg-background/50">
    <button type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open} className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-xs font-medium hover:bg-muted/50">
      <span className="inline-flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-primary" /> Implementation steps <span className="font-normal text-muted-foreground">({recommendation.steps.length})</span></span>
      <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`} />
    </button>
    {open && <div className="space-y-4 border-t px-4 py-4">
      <ol className="space-y-3">
        {recommendation.steps.map((step, index) => <li key={step} className="flex gap-3 text-xs leading-relaxed text-muted-foreground"><span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 font-mono text-[10px] font-semibold text-primary">{index + 1}</span><span>{step}</span></li>)}
      </ol>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg bg-emerald-500/5 p-3"><p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400"><Target className="h-3.5 w-3.5" /> Validation target</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{recommendation.validationTarget}</p></div>
        <div className="rounded-lg bg-amber-500/5 p-3"><p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400"><ShieldAlert className="h-3.5 w-3.5" /> Guardrail</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{recommendation.guardrail}</p></div>
      </div>
    </div>}
  </div>;
}