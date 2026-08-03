import { ArrowLeft, Bot, CheckCircle2, CircleX, Stethoscope, TrendingUp } from "lucide-react";
import { Link, useParams } from "react-router";
import { FailurePatternSummary } from "@/components/ea-bridge/FailurePatternSummary";

const trade = {
  id: "ea-trade-1840",
  ticket: "ticket-98421",
  correlationId: "corr-cmd-1840",
  symbol: "XAUUSD",
  direction: "BUY",
  volume: 0.05,
  entry: 2384.25,
  exit: 2378.25,
  stopLoss: 2378.25,
  takeProfit: 2396.25,
  result: "SL",
  pnl: -30,
  openedAt: "2026-08-03T08:31:20Z",
  closedAt: "2026-08-03T09:06:42Z",
  terminal: "EA Terminal A",
  broker: "ICMarkets-Demo",
  diagnosis: "Counter-trend entry during a ranging market produced a false bullish continuation signal.",
  confidence: 88,
  indicators: [
    { label: "Trend", value: "Bullish", state: "PASS" },
    { label: "EMA alignment", value: "Bullish", state: "PASS" },
    { label: "RSI", value: "61.4", state: "PASS" },
    { label: "ATR", value: "High · 8.2", state: "RISK" },
    { label: "Volume", value: "Normal", state: "PASS" },
    { label: "Market regime", value: "Ranging", state: "FAIL" },
    { label: "Session", value: "Asia", state: "RISK" },
    { label: "ACR zone", value: "Mitigated", state: "FAIL" },
  ],
  timeline: [
    { label: "Signal generated", detail: "BUY setup accepted by precision engine", time: "08:31:18" },
    { label: "Command acknowledged", detail: "EA accepted corr-cmd-1840 in 21ms", time: "08:31:20" },
    { label: "Order filled", detail: "MT5 ticket-98421 opened at 2384.25", time: "08:31:20" },
    { label: "Stop loss filled", detail: "Position closed at 2378.25", time: "09:06:42" },
    { label: "Diagnostic complete", detail: "Failure evidence classified with 88% confidence", time: "09:06:44" },
  ],
};

const stateTone: Record<string, string> = { PASS: "bg-emerald-500/10 text-emerald-500", RISK: "bg-amber-500/10 text-amber-500", FAIL: "bg-rose-500/10 text-rose-500" };

export function EaBridgeTradeDiagnostics() {
  const { tradeId } = useParams();
  if (tradeId !== trade.id) return <div className="mx-auto max-w-3xl p-8 text-center"><CircleX className="mx-auto h-8 w-8 text-muted-foreground" /><h1 className="mt-4 text-xl font-semibold">Trade diagnostic not found</h1><p className="mt-2 text-sm text-muted-foreground">No synchronized EA trade matches `{tradeId}`.</p><Link to="/ea-bridge" className="mt-5 inline-flex rounded-lg border px-3 py-2 text-xs hover:bg-muted">Return to EA Bridge</Link></div>;

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><Link to="/ea-bridge" className="mb-4 inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"><ArrowLeft className="h-3.5 w-3.5" /> EA Bridge</Link><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><Stethoscope className="h-4 w-4" /> Per-trade evidence</div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Trade diagnostic · {trade.ticket}</h1><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Execution truth from MT5 correlated with the market snapshot used at entry.</p></div><div className="flex items-center gap-2"><span className="rounded-full bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-500">RESULT {trade.result}</span><span className="rounded-full border px-3 py-1 font-mono text-xs text-muted-foreground">{trade.correlationId}</span></div></header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Direction / lot" value={`${trade.direction} · ${trade.volume.toFixed(2)}`} detail={`${trade.symbol} via ${trade.terminal}`} tone="text-emerald-500" /><Metric label="Entry / exit" value={`${trade.entry.toFixed(2)} / ${trade.exit.toFixed(2)}`} detail={`${trade.broker} fill prices`} /><Metric label="Realized P/L" value={`-$${Math.abs(trade.pnl).toFixed(2)}`} detail="Stop loss execution" tone="text-rose-500" /><Metric label="Diagnosis confidence" value={`${trade.confidence}%`} detail="Evidence classification" tone="text-amber-500" /></section>

    <section aria-label="Trade failure diagnosis" className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-5"><div className="flex gap-3"><TrendingUp className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" /><div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-rose-500">Likely failure cause</p><h2 className="mt-1 text-lg font-semibold">Regime filter false positive</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{trade.diagnosis}</p></div></div></section>

    <section className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(340px,0.9fr)]"><article aria-label="Entry market snapshot" className="rounded-xl border bg-card shadow-sm"><PanelHeader icon={Stethoscope} title="Entry market snapshot" detail="Technical evidence captured before the EA accepted the order." /><div className="grid gap-3 p-5 sm:grid-cols-2">{trade.indicators.map((indicator) => <div key={indicator.label} className="flex items-center justify-between gap-3 rounded-lg border bg-muted/20 p-3"><div><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{indicator.label}</p><p className="mt-1 font-mono text-sm font-semibold">{indicator.value}</p></div><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${stateTone[indicator.state]}`}>{indicator.state}</span></div>)}</div></article><article aria-label="EA trade lifecycle" className="rounded-xl border bg-card shadow-sm"><PanelHeader icon={Bot} title="EA trade lifecycle" detail="Correlated engine, bridge, and MT5 events." /><ol className="space-y-0 p-5">{trade.timeline.map((event, index) => <li key={event.label} className="grid grid-cols-[20px_1fr_auto] gap-3"><div className="flex flex-col items-center"><CheckCircle2 className="h-4 w-4 text-emerald-500" />{index < trade.timeline.length - 1 && <span className="h-full w-px bg-border" />}</div><div className="pb-5"><p className="text-xs font-semibold">{event.label}</p><p className="mt-1 text-[10px] text-muted-foreground">{event.detail}</p></div><time className="font-mono text-[10px] text-muted-foreground">{event.time}</time></li>)}</ol></article></section>

    <article className="rounded-xl border bg-card p-5"><div className="grid gap-3 sm:grid-cols-4"><Level label="Stop loss" value={trade.stopLoss} tone="text-rose-500" /><Level label="Take profit" value={trade.takeProfit} tone="text-emerald-500" /><Level label="Opened" value={new Date(trade.openedAt).toLocaleString()} /><Level label="Closed" value={new Date(trade.closedAt).toLocaleString()} /></div></article>
    <FailurePatternSummary />
  </div>;
}

function PanelHeader({ icon: Icon, title, detail }: { icon: typeof Bot; title: string; detail: string }) { return <div className="flex items-start gap-3 border-b p-5"><span className="rounded-lg bg-primary/10 p-2 text-primary"><Icon className="h-4 w-4" /></span><div><h2 className="font-semibold">{title}</h2><p className="mt-0.5 text-xs text-muted-foreground">{detail}</p></div></div>; }
function Metric({ label, value, detail, tone = "text-foreground" }: { label: string; value: string; detail: string; tone?: string }) { return <article className="rounded-xl border bg-card p-4"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></article>; }
function Level({ label, value, tone = "text-foreground" }: { label: string; value: number | string; tone?: string }) { return <div><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-xs font-semibold ${tone}`}>{typeof value === "number" ? value.toFixed(2) : value}</p></div>; }
