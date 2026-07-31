import { AlertTriangle, CheckCircle2, Gauge, Target } from "lucide-react";
import type { SuccessMetric, SuccessMetricStatus } from "@/data/diagnostic-improvements";

const statusMeta: Record<SuccessMetricStatus, { label: string; icon: typeof Gauge; className: string }> = {
  ACHIEVED: { label: "Achieved", icon: CheckCircle2, className: "bg-emerald-500/10 text-emerald-500" },
  ON_TRACK: { label: "On track", icon: Gauge, className: "bg-sky-500/10 text-sky-500" },
  AT_RISK: { label: "At risk", icon: AlertTriangle, className: "bg-amber-500/10 text-amber-500" },
};

export function SuccessMetrics({ metrics }: { metrics: SuccessMetric[] }) {
  if (metrics.length === 0) {
    return <div className="rounded-lg border border-dashed p-8 text-center"><Target className="mx-auto h-6 w-6 text-muted-foreground" /><p className="mt-3 text-sm font-medium">No success metrics defined</p><p className="mt-1 text-xs text-muted-foreground">Set a measurable target to track an improvement.</p></div>;
  }

  return <section aria-labelledby="success-metrics-title" className="rounded-xl border bg-card p-5 shadow-sm">
    <div><h2 id="success-metrics-title" className="font-semibold">Success metrics</h2><p className="mt-1 text-xs text-muted-foreground">Measure each improvement against its evidence-based target.</p></div>
    <div className="mt-5 grid gap-3 md:grid-cols-2">
      {metrics.map((metric) => {
        const meta = statusMeta[metric.status];
        const Icon = meta.icon;
        const progress = Math.min(100, Math.max(0, metric.progress));
        return <article key={metric.id} className="rounded-lg border bg-background/50 p-4">
          <div className="flex items-start justify-between gap-3"><div><h3 className="text-sm font-medium">{metric.label}</h3><p className="mt-1 text-xs text-muted-foreground">{metric.detail}</p></div><span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-semibold ${meta.className}`}><Icon className="h-3 w-3" />{meta.label}</span></div>
          <div className="mt-4 flex items-end justify-between gap-3"><div><p className="text-[10px] uppercase tracking-wide text-muted-foreground">Current</p><p className="mt-1 font-mono text-xl font-semibold">{metric.current}</p></div><div className="text-right"><p className="text-[10px] uppercase tracking-wide text-muted-foreground">Target</p><p className="mt-1 font-mono text-sm font-semibold text-primary">{metric.target}</p></div></div>
          <div className="mt-4"><div className="h-2 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${metric.status === "AT_RISK" ? "bg-amber-500" : metric.status === "ACHIEVED" ? "bg-emerald-500" : "bg-sky-500"}`} style={{ width: `${progress}%` }} /></div><p className="mt-1 text-right text-[10px] text-muted-foreground">{progress}% toward target</p></div>
        </article>;
      })}
    </div>
  </section>;
}