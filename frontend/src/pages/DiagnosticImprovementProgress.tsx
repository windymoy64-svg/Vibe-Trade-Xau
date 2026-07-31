import {
  ArrowLeft,
  ArrowUpRight,
  CheckCircle2,
  ClipboardList,
  FlaskConical,
  Gauge,
  History,
  Target,
  TrendingUp,
} from "lucide-react";
import { Link } from "react-router";
import { ImprovementTimeline } from "@/components/diagnostics/ImprovementTimeline";
import { ImprovementActivityLog } from "@/components/diagnostics/ImprovementActivityLog";
import { ImprovementReportExport } from "@/components/diagnostics/ImprovementReportExport";
import { LossReductionChart } from "@/components/diagnostics/LossReductionChart";
import { SuccessMetrics } from "@/components/diagnostics/SuccessMetrics";
import { diagnosticImprovementProgressStub } from "@/data/diagnostic-improvements";

export function DiagnosticImprovementProgress() {
  const { summary, timeline, lossReduction, successMetrics, activities } = diagnosticImprovementProgressStub;
  const summaryCards = [
    { icon: ClipboardList, label: "Tracked improvements", value: String(summary.tracked), detail: `${summary.active} active, ${summary.validated} validated` },
    { icon: Gauge, label: "Validation coverage", value: `${summary.validationCoverage}%`, detail: `${summary.active} changes have measurable targets`, tone: "text-sky-500" },
    { icon: TrendingUp, label: "Best observed change", value: `−${Math.abs(summary.bestObservedChange)}%`, detail: summary.bestObservedLabel, tone: "text-emerald-500" },
  ];
  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header>
      <Link to="/diagnostics/recommendations" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Recommendations
      </Link>
      <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary">
            <FlaskConical className="h-4 w-4" /> Continuous validation
            <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">Preview data</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Improvement progress</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Track every strategy change from recommendation to evidence-backed validation.
          </p>
        </div>
        <div className="flex flex-wrap gap-2"><Link to="/diagnostics/recommendations" className="inline-flex w-fit items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted">Review recommendations <ArrowUpRight className="h-4 w-4" /></Link><ImprovementReportExport timeline={timeline} lossReduction={lossReduction} metrics={successMetrics} activities={activities} /></div>
      </div>
    </header>

    <section aria-label="Improvement summary" className="grid gap-3 sm:grid-cols-3">
      {summaryCards.map(({ icon: Icon, label, value, detail, tone = "text-foreground" }) => <div key={label} className="rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex items-center justify-between text-xs text-muted-foreground"><span>{label}</span><Icon className="h-4 w-4" /></div>
        <p className={`mt-3 text-3xl font-semibold ${tone}`}>{value}</p>
        <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
      </div>)}
    </section>

    <LossReductionChart data={lossReduction} />
    <SuccessMetrics metrics={successMetrics} />
    <ImprovementActivityLog activities={activities} />

    <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="rounded-xl border bg-card shadow-sm">
        <div className="flex flex-col justify-between gap-2 border-b p-5 sm:flex-row sm:items-center">
          <div><h2 className="font-semibold">Active improvements</h2><p className="mt-1 text-xs text-muted-foreground">Controlled strategy changes currently collecting evidence.</p></div>
          <span className="w-fit rounded-full bg-sky-500/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-sky-500">3 in progress</span>
        </div>
        <div className="space-y-3 p-5">
          <ImprovementTimeline events={timeline} />
          <div className="grid gap-3 sm:grid-cols-2">
            <PlaceholderBlock icon={Target} title="Baseline & target" detail="Compare a diagnosed baseline with a measurable success target." />
            <PlaceholderBlock icon={History} title="Change history" detail="Keep an auditable timeline of strategy modifications and outcomes." />
          </div>
        </div>
      </div>

      <aside className="h-fit space-y-5 rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><FlaskConical className="h-5 w-5" /></div>
        <div><h2 className="font-semibold">Evidence loop</h2><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Validate one isolated change at a time so performance movement can be attributed to the correct control.</p></div>
        <ol className="space-y-3 border-t pt-4">
          {[
            "Select an evidence-backed recommendation",
            "Record the strategy change and baseline",
            "Collect trades over the validation window",
            "Compare the result against the target",
          ].map((step, index) => <li key={step} className="flex gap-3 text-xs text-muted-foreground"><span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-[10px] text-foreground">{index + 1}</span><span className="pt-0.5">{step}</span></li>)}
        </ol>
        <div className="rounded-lg bg-emerald-500/5 p-3 text-xs text-muted-foreground"><CheckCircle2 className="mb-2 h-4 w-4 text-emerald-500" /><strong className="text-foreground">Goal:</strong> turn every applied recommendation into measurable learning for the next diagnostic cycle.</div>
      </aside>
    </section>
  </div>;
}

function PlaceholderBlock({ icon: Icon, title, detail }: { icon: typeof Target; title: string; detail: string }) {
  return <div className="rounded-lg bg-muted/40 p-4"><Icon className="h-4 w-4 text-muted-foreground" /><h3 className="mt-3 text-sm font-medium">{title}</h3><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{detail}</p></div>;
}