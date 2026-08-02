import { CheckCircle2, Scale } from "lucide-react";
import type { FibonacciValuationPreview } from "@/data/precision-execution";

export function FibonacciValuationPanel({ valuation }: { valuation: FibonacciValuationPreview }) {
  const range = valuation.swingHigh - valuation.swingLow;
  const currentPosition = ((valuation.swingHigh - valuation.currentPrice) / range) * 100;
  const setupPosition = ((valuation.swingHigh - valuation.setupZoneMidpoint) / range) * 100;

  return <article className="overflow-hidden rounded-xl border bg-card shadow-sm" aria-label="Fibonacci premium discount panel">
    <div className="flex items-start gap-3 border-b p-5"><span className="rounded-lg bg-amber-500/10 p-2 text-amber-500"><Scale className="h-4 w-4" /></span><div><h2 className="font-semibold">Fibonacci valuation</h2><p className="mt-0.5 text-xs text-muted-foreground">HTF dealing range with a strict 50% equilibrium gate.</p></div></div>
    <div className="grid gap-5 p-5 md:grid-cols-[minmax(220px,0.8fr)_minmax(0,1.2fr)]">
      <div className="relative h-64 overflow-hidden rounded-xl border bg-background">
        <div className="absolute inset-x-0 top-0 h-1/2 bg-rose-500/10"><span className="absolute left-3 top-3 text-[10px] font-semibold text-rose-500">PREMIUM · SELL AREA</span></div>
        <div className="absolute inset-x-0 bottom-0 h-1/2 bg-emerald-500/10"><span className="absolute bottom-3 left-3 text-[10px] font-semibold text-emerald-500">DISCOUNT · BUY AREA</span></div>
        <div className="absolute inset-x-0 top-1/2 border-t border-dashed border-amber-500"><span className="absolute right-2 -translate-y-1/2 bg-background px-1 font-mono text-[9px] text-amber-500">EQ {valuation.equilibrium.toFixed(2)}</span></div>
        <PriceMarker label="CURRENT" value={valuation.currentPrice} position={currentPosition} tone="bg-sky-500" />
        <PriceMarker label="SETUP" value={valuation.setupZoneMidpoint} position={setupPosition} tone="bg-emerald-500" />
        <span className="absolute right-2 top-2 font-mono text-[9px] text-muted-foreground">{valuation.swingHigh.toFixed(2)}</span><span className="absolute bottom-2 right-2 font-mono text-[9px] text-muted-foreground">{valuation.swingLow.toFixed(2)}</span>
      </div>
      <div className="space-y-3"><div className="grid grid-cols-2 gap-3"><Metric label="Swing high" value={valuation.swingHigh} /><Metric label="Swing low" value={valuation.swingLow} /><Metric label="Equilibrium 50%" value={valuation.equilibrium} /><Metric label="Setup midpoint" value={valuation.setupZoneMidpoint} /></div><div className={`rounded-lg border p-4 ${valuation.eligible ? "border-emerald-500/30 bg-emerald-500/5" : "border-rose-500/30 bg-rose-500/5"}`}><div className="flex items-center gap-2 text-sm font-semibold"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> {valuation.setupDirection} setup {valuation.eligible ? "eligible" : "blocked"}</div><p className="mt-2 text-xs leading-relaxed text-muted-foreground">Zone midpoint is in <strong className="text-emerald-500">{valuation.setupValuation}</strong>, below equilibrium. The valuation gate permits a Buy setup.</p></div></div>
    </div>
  </article>;
}

function PriceMarker({ label, value, position, tone }: { label: string; value: number; position: number; tone: string }) { return <div className="absolute inset-x-0 flex items-center" style={{ top: `${Math.max(4, Math.min(96, position))}%` }}><span className={`h-2 w-2 -translate-x-1/2 rounded-full ${tone}`} /><span className="h-px flex-1 bg-border" /><span className="mr-2 bg-background px-1 font-mono text-[9px]">{label} {value.toFixed(2)}</span></div>; }
function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-lg border bg-background/70 p-3"><p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm font-semibold">{value.toFixed(2)}</p></div>; }
