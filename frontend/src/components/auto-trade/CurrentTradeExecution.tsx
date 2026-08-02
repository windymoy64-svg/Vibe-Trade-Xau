import { Activity, Clock3, ShieldAlert, Target } from "lucide-react";
import type { AutoTradePreviewData } from "@/data/auto-trade";

type Execution = AutoTradePreviewData["currentExecution"];

export function CurrentTradeExecution({ execution }: { execution: Execution }) {
  const targetDistance = Math.abs(execution.takeProfit - execution.entryPrice);
  const travelled = execution.direction === "BUY" ? execution.currentPrice - execution.entryPrice : execution.entryPrice - execution.currentPrice;
  const targetProgress = targetDistance > 0 ? Math.max(0, Math.min(100, (travelled / targetDistance) * 100)) : 0;
  const directionTone = execution.direction === "BUY" ? "text-emerald-500" : "text-rose-500";

  return <article className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 shadow-sm" aria-labelledby="current-execution-title">
    <div className="flex flex-col justify-between gap-3 border-b border-emerald-500/20 p-5 sm:flex-row sm:items-start">
      <div className="flex items-start gap-3"><span className="rounded-lg bg-emerald-500/10 p-2 text-emerald-500"><Activity className="h-4 w-4" /></span><div><div className="flex flex-wrap items-center gap-2"><h2 id="current-execution-title" className="font-semibold">Current trade execution</h2><span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-500">{execution.status}</span></div><p className="mt-0.5 text-xs text-muted-foreground">Preview position status · no broker exposure</p></div></div>
      <div className="text-left sm:text-right"><p className={`font-mono text-lg font-semibold ${directionTone}`}>{execution.direction} {execution.symbol}</p><p className="text-[10px] text-muted-foreground">#{execution.id}</p></div>
    </div>
    <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-4"><ExecutionMetric label="Entry" value={execution.entryPrice.toFixed(2)} /><ExecutionMetric label="Current" value={execution.currentPrice.toFixed(2)} tone={directionTone} /><ExecutionMetric label="Floating result" value={`${execution.floatingR >= 0 ? "+" : ""}${execution.floatingR.toFixed(2)}R`} tone={execution.floatingR >= 0 ? "text-emerald-500" : "text-rose-500"} /><ExecutionMetric label="Position size" value={`${execution.lotSize.toFixed(2)} lot`} /></div>
    <div className="grid gap-4 border-t border-emerald-500/20 p-5 sm:grid-cols-2">
      <div className="space-y-3"><PriceGate icon={ShieldAlert} label="Stop loss" value={execution.stopLoss.toFixed(2)} tone="text-rose-500" /><PriceGate icon={Target} label="Take profit" value={execution.takeProfit.toFixed(2)} tone="text-emerald-500" /></div>
      <div><div className="flex items-center justify-between text-xs"><span className="text-muted-foreground">Progress toward TP</span><strong>{targetProgress.toFixed(0)}%</strong></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${targetProgress}%` }} /></div><div className="mt-4 flex flex-wrap justify-between gap-2 text-[10px] text-muted-foreground"><span className="flex items-center gap-1"><Clock3 className="h-3 w-3" /> Opened {new Date(execution.openedAt).toLocaleTimeString()}</span><span>Updated {new Date(execution.updatedAt).toLocaleTimeString()}</span></div></div>
    </div>
  </article>;
}

function ExecutionMetric({ label, value, tone = "text-foreground" }: { label: string; value: string; tone?: string }) { return <div className="rounded-lg bg-background/70 p-3"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-sm font-semibold ${tone}`}>{value}</p></div>; }
function PriceGate({ icon: Icon, label, value, tone }: { icon: typeof Target; label: string; value: string; tone: string }) { return <div className="flex items-center justify-between rounded-lg bg-background/70 p-3"><span className="flex items-center gap-2 text-xs text-muted-foreground"><Icon className={`h-3.5 w-3.5 ${tone}`} /> {label}</span><strong className={`font-mono text-xs ${tone}`}>{value}</strong></div>; }