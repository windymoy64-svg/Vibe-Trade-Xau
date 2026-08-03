import { Activity, Database, RefreshCw, Server, Terminal } from "lucide-react";
import { Link } from "react-router";
import { mt5DirectPreview, type Mt5PipelineStatus } from "@/data/mt5-direct";
import { Mt5ConnectionIndicator } from "@/components/mt5-direct/Mt5ConnectionIndicator";
import { LiveOhlcChart } from "@/components/mt5-direct/LiveOhlcChart";
import { Mt5DiagnosticTradeList } from "@/components/mt5-direct/Mt5DiagnosticTradeList";
import { Mt5FailurePatternSummary } from "@/components/mt5-direct/Mt5FailurePatternSummary";

const statusTone: Record<Mt5PipelineStatus, string> = {
  HEALTHY: "bg-emerald-500/10 text-emerald-500",
  DEGRADED: "bg-amber-500/10 text-amber-500",
  OFFLINE: "bg-rose-500/10 text-rose-500",
};

export function Mt5ProductionDiagnostics() {
  const data = mt5DirectPreview;
  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><Link to="/ea-bridge" className="mb-4 inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"><Activity className="h-3.5 w-3.5" /> EA Bridge alternative</Link><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><Terminal className="h-4 w-4" /> Native MetaTrader5 Python</div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Production diagnostics</h1><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Observe direct terminal connectivity, broker-native market data ingestion, and diagnostic evidence coverage for live XAUUSD trades.</p></div><button type="button" className="inline-flex items-center justify-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"><RefreshCw className="h-3.5 w-3.5" /> Refresh snapshot</button></header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric label="Ticks today" value={data.metrics.ticksToday.toLocaleString()} detail="Native XAUUSD feed" /><Metric label="OHLC bars" value={data.metrics.barsIngested.toLocaleString()} detail="Four synchronized timeframes" /><Metric label="Trades analyzed" value={String(data.metrics.tradesAnalyzed)} detail="Production executions" /><Metric label="Evidence coverage" value={`${data.metrics.diagnosticCoverage.toFixed(1)}%`} detail="Indicator snapshots complete" tone="text-emerald-500" /></section>

    <Mt5ConnectionIndicator terminal={data.terminal} />
    <LiveOhlcChart symbol={data.ohlc.symbol} initialTimeframe={data.ohlc.timeframe} initialBars={data.ohlc.bars} />

    <section><article aria-label="MT5 diagnostic pipeline" className="rounded-xl border bg-card shadow-sm"><PanelHeader icon={Database} title="Diagnostic pipeline" detail="Connection, data ingestion, and analysis readiness." /><ol className="divide-y">{data.pipeline.map((step, index) => <li key={step.id} className="flex gap-3 p-4"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-xs font-semibold">{index + 1}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-semibold">{step.label}</p><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${statusTone[step.status]}`}>{step.status}</span></div><p className="mt-1 text-[10px] text-muted-foreground">{step.detail}</p></div></li>)}</ol></article></section>

    <Mt5DiagnosticTradeList trades={data.trades} />
    <Mt5FailurePatternSummary />
  </div>;
}

function PanelHeader({ icon: Icon, title, detail }: { icon: typeof Server; title: string; detail: string }) { return <div className="flex items-start gap-3 border-b p-5"><span className="rounded-lg bg-primary/10 p-2 text-primary"><Icon className="h-4 w-4" /></span><div><h2 className="font-semibold">{title}</h2><p className="mt-0.5 text-xs text-muted-foreground">{detail}</p></div></div>; }
function Metric({ label, value, detail, tone = "text-foreground" }: { label: string; value: string; detail: string; tone?: string }) { return <article className="rounded-xl border bg-card p-4"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></article>; }
