import { CircleCheck, CircleX } from "lucide-react";
import type { AcrZonePreview } from "@/data/precision-execution";

export function ZoneStatusIndicator({ zone }: { zone: AcrZonePreview }) {
  const fresh = zone.status === "FRESH";
  const Icon = fresh ? CircleCheck : CircleX;
  const evidence = fresh
    ? `No candle has closed ${zone.direction === "BULLISH" ? "below" : "above"} the zone boundary.`
    : `${zone.invalidation?.time}: close ${zone.invalidation?.close.toFixed(2)} crossed the ${zone.direction === "BULLISH" ? "low" : "high"} boundary.`;

  return <div className={`rounded-lg border px-3 py-2 ${fresh ? "border-emerald-500/30 bg-emerald-500/10" : "border-rose-500/30 bg-rose-500/10"}`} aria-label={`${zone.direction.toLowerCase()} zone ${zone.status.toLowerCase()}`}>
    <div className={`flex items-center gap-1.5 text-[10px] font-semibold ${fresh ? "text-emerald-500" : "text-rose-500"}`}><Icon className="h-3.5 w-3.5" /> {fresh ? "FRESH ZONE" : "INVALID ZONE"}</div>
    <p className="mt-1 max-w-56 text-[9px] leading-relaxed text-muted-foreground">{evidence}</p>
  </div>;
}
