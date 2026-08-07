import { useEffect, useState } from "react";
import { BarChart3, CalendarDays, Filter, Gauge, Loader2, Target, TrendingDown, TrendingUp } from "lucide-react";
import { CommonCauseStats } from "@/components/diagnostics/CommonCauseStats";
import { SuspectedCauseChart } from "@/components/diagnostics/SuspectedCauseChart";
import { RecentTrades } from "@/components/diagnostics/RecentTrades";
import { QuickInsight } from "@/components/diagnostics/QuickInsight";
import { api, type DiagnosticsDashboardLive } from "@/lib/api";

function MetricCard({ icon: Icon, label, value, detail, tone = "text-foreground" }: { icon: typeof Target; label: string; value: string; detail: string; tone?: string }) {
  return <div className="rounded-xl border bg-card p-5 shadow-sm"><div className="flex items-center justify-between"><span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span><Icon className="h-4 w-4 text-muted-foreground" /></div><div className={`mt-3 text-3xl font-semibold tracking-tight ${tone}`}>{value}</div><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div>;
}

export function DiagnosticsDashboard() {
  const [dashboard, setDashboard] = useState<DiagnosticsDashboardLive | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const load = () => {
      api.getDiagnosticsDashboard()
        .then((data) => { if (!active) return; setDashboard(data); setError(null); })
        .catch((value) => { if (!active) return; setError(value instanceof Error ? value.message : "Gagal memuat dashboard"); setDashboard(null); })
        .finally(() => { if (active) setLoading(false); });
    };
    load();
    const timer = window.setInterval(load, 15_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const noData = !dashboard || dashboard.summary.totalTrades === 0;

  return <div className="mx-auto max-w-7xl space-y-5 p-4 sm:space-y-6 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><Gauge className="h-4 w-4" /> Production strategy diagnostics {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : noData ? <span className="rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] text-rose-500">NO DATA</span> : <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-500">LIVE DATA</span>}</div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Diagnostic dashboard</h1><p className="mt-1 text-sm text-muted-foreground">Understand why your XAUUSD trades win or lose.</p></div><div className="flex w-full items-center gap-2 sm:w-auto"><button className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm hover:bg-muted sm:flex-none"><CalendarDays className="h-4 w-4" /> Last 30 days</button><button className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"><Filter className="h-4 w-4" /><span className="hidden sm:inline">Filter</span></button></div></header>
    {error && <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs text-rose-500">{error}</div>}
    {noData && !loading && (
      <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
        <p className="font-medium">Belum ada diagnostic trades</p>
        <p className="mt-1 text-xs">Eksekusi atau import trade MT5 untuk mulai analisis. Diagnostics sinkron otomatis setiap 15 detik setelah data tersedia.</p>
      </div>
    )}
    {dashboard && !noData && (
      <>
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><MetricCard icon={BarChart3} label="Total trades" value={dashboard.summary.totalTrades.toLocaleString()} detail="Closed diagnostic trades" /><MetricCard icon={TrendingUp} label="Winning trades" value={dashboard.summary.winningTrades.toLocaleString()} detail={dashboard.summary.totalTrades ? `${((dashboard.summary.winningTrades / dashboard.summary.totalTrades) * 100).toFixed(1)}% win rate` : "0% win rate"} tone="text-emerald-500" /><MetricCard icon={TrendingDown} label="Losing trades" value={dashboard.summary.losingTrades.toLocaleString()} detail={dashboard.summary.totalTrades ? `${((dashboard.summary.losingTrades / dashboard.summary.totalTrades) * 100).toFixed(1)}% of all trades` : "0% of all trades"} tone="text-rose-500" /><MetricCard icon={Target} label="Loss rate" value={`${dashboard.summary.lossRate}%`} detail="Diagnostic losses" tone="text-amber-500" /></section>
        <section className="grid gap-6 lg:grid-cols-[1.35fr_1fr]"><CommonCauseStats causes={dashboard.causes.map((cause, index) => ({ ...cause, colorClass: ["bg-rose-500", "bg-amber-500", "bg-sky-500", "bg-violet-500"][index % 4] }))} totalLosses={dashboard.summary.losingTrades} contextFilterPercentage={dashboard.contextFilterPercentage} /><SuspectedCauseChart data={dashboard.recentTrades.map((trade) => ({ label: new Date(trade.entryTime).toLocaleDateString(), wins: trade.result === "TP" ? 1 : 0, losses: trade.result === "SL" ? 1 : 0 }))} /></section>
        <RecentTrades trades={dashboard.recentTrades.map((trade) => ({ id: trade.id, time: new Date(trade.entryTime).toLocaleString(), direction: trade.direction as "BUY" | "SELL", result: trade.result as "TP" | "SL", reason: trade.suspectedReason, profitLoss: trade.profitLoss != null ? `${trade.profitLoss >= 0 ? "+" : ""}${trade.profitLoss.toFixed(2)}` : "—" }))} />
        {dashboard.insight && <QuickInsight {...dashboard.insight} />}
      </>
    )}
  </div>;
}