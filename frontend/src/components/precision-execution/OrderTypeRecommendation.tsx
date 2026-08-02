import { Check, Clock3, OctagonX, Route } from "lucide-react";
import type { OrderTypeRecommendationPreview } from "@/data/precision-execution";

export function OrderTypeRecommendation({ recommendation }: { recommendation: OrderTypeRecommendationPreview }) {
  return <article className="overflow-hidden rounded-xl border border-amber-500/30 bg-card shadow-sm" aria-label="Order type recommendation">
    <div className="grid lg:grid-cols-[minmax(260px,0.75fr)_minmax(0,1.25fr)]">
      <div className="bg-amber-500/5 p-5"><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-amber-500"><Route className="h-4 w-4" /> Order decision</div><p className="mt-4 text-xs text-muted-foreground">Recommended execution</p><h2 className="mt-1 font-mono text-3xl font-bold text-amber-500">{recommendation.recommendation}</h2><span className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-[10px] font-semibold text-amber-500"><Clock3 className="h-3 w-3" /> {recommendation.status}</span><div className="mt-5 grid grid-cols-2 gap-3"><Metric label="Limit price" value={recommendation.entryPrice} /><Metric label="Distance" value={recommendation.distancePoints} suffix=" pts" /></div><p className="mt-4 text-[10px] leading-relaxed text-muted-foreground">Preview only. This recommendation cannot place or route an order.</p></div>
      <div className="p-5"><h3 className="text-sm font-semibold">Mechanical decision checks</h3><div className="mt-3 space-y-2">{recommendation.checks.map((check) => <div key={check.label} className="flex items-start gap-3 rounded-lg border bg-background/60 p-3"><span className={`mt-0.5 rounded-full p-1 ${check.passed ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>{check.passed ? <Check className="h-3 w-3" /> : <OctagonX className="h-3 w-3" />}</span><div><p className="text-xs font-medium">{check.label}</p><p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">{check.detail}</p></div></div>)}</div></div>
    </div>
  </article>;
}

function Metric({ label, value, suffix = "" }: { label: string; value: number; suffix?: string }) { return <div className="rounded-lg border bg-background/70 p-3"><p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm font-semibold">{value.toFixed(2)}{suffix}</p></div>; }
