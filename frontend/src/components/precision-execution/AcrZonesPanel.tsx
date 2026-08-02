import { ShieldCheck, TrendingDown, TrendingUp } from "lucide-react";
import type { AcrZonePreview } from "@/data/precision-execution";
import { ZoneStatusIndicator } from "@/components/precision-execution/ZoneStatusIndicator";

export function AcrZonesPanel({ zones }: { zones: AcrZonePreview[] }) {
  return <div className="grid gap-4 lg:grid-cols-2" aria-label="ACR zone panel">
    {zones.map((zone) => {
      const bullish = zone.direction === "BULLISH";
      const Icon = bullish ? TrendingUp : TrendingDown;
      return <article key={zone.id} className={`overflow-hidden rounded-xl border ${bullish ? "border-emerald-500/30 bg-emerald-500/5" : "border-rose-500/30 bg-rose-500/5"}`}>
        <div className="flex items-start justify-between gap-4 border-b border-inherit p-4">
          <div className="flex items-center gap-3"><span className={`rounded-lg p-2 ${bullish ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}><Icon className="h-4 w-4" /></span><div><h3 className="text-sm font-semibold">{bullish ? "Bullish ACR" : "Bearish ACR"}</h3><p className="mt-0.5 text-[10px] text-muted-foreground">{zone.timeframe} · formed {zone.formedAt}</p></div></div>
          <ZoneStatusIndicator zone={zone} />
        </div>
        <div className="grid grid-cols-2 gap-px bg-border/60"><Metric label="Zone low" value={zone.low} /><Metric label="Zone high" value={zone.high} /><Metric label="Trigger close" value={zone.triggerClose} /><Metric label={bullish ? "Previous high" : "Previous low"} value={zone.referenceBoundary} /></div>
        <div className="flex items-start gap-2 p-4 text-xs"><ShieldCheck className={`mt-0.5 h-4 w-4 shrink-0 ${bullish ? "text-emerald-500" : "text-rose-500"}`} /><p className="text-muted-foreground"><strong className="text-foreground">Rule confirmed:</strong> Close {bullish ? "> previous High" : "< previous Low"}. Invalidate when a candle closes {bullish ? "below zone low" : "above zone high"}.</p></div>
      </article>;
    })}
  </div>;
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="bg-card/80 p-3"><p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm font-semibold">{value.toFixed(2)}</p></div>;
}
