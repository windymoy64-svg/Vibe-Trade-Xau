import { useEffect, useState } from "react";
import { BarChart3, CalendarDays, Filter, Gauge, Loader2, Target, TrendingDown, TrendingUp } from "lucide-react";
import { CommonCauseStats } from "@/components/diagnostics/CommonCauseStats";
import { SuspectedCauseChart } from "@/components/diagnostics/SuspectedCauseChart";
import { RecentTrades } from "@/components/diagnostics/RecentTrades";
import { QuickInsight } from "@/components/diagnostics/QuickInsight";
import { diagnosticsDashboardStub, type DiagnosticsDashboardData } from "@/data/diagnostics-dashboard";
import { api } from "@/lib/api";

function MetricCard({ icon: Icon, label, value, detail, tone = "text-foreground" }: { icon: typeof Target; label: string; value: string; detail: string; tone?: string }) {
  return <div className="rounded-xl border bg-card p-5 shadow-sm"><div className="flex items-center justify-between"><span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</span><Icon className="h-4 w-4 text-muted-foreground" /></div><div className={`mt-3 text-3xl font-semibold tracking-tight ${tone}`}>{value}</div><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div>;
}

export function DiagnosticsDashboard() {
  const [dashboard, setDashboard] = useState<DiagnosticsDashboardData>(diagnosticsDashboardStub);
  const [usingPreviewData, setUsingPreviewData] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api.getDiagnosticsDashboard()
      .then((data) => {
        if (!active) return;
        setDashboard(data);
        setUsingPreviewData(false);
      })
      .catch(() => {
        if (!active) return;
        setDashboard(diagnosticsDashboardStub);
        setUsingPreviewData(true);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const { summary, causes, weeklyDistribution, recentTrades, insight, contextFilterPercentage } = dashboard;

  return <div className="mx-auto max-w-7xl space-y-5 p-4 sm:space-y-6 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><Gauge className="h-4 w-4" /> Production strategy diagnostics {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : usingPreviewData ? <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">Preview data</span> : null}</div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Diagnostic dashboard</h1><p className="mt-1 text-sm text-muted-foreground">Understand why your XAUUSD trades win or lose.</p></div><div className="flex w-full items-center gap-2 sm:w-auto"><button className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm hover:bg-muted sm:flex-none"><CalendarDays className="h-4 w-4" /> Last 30 days</button><button className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"><Filter className="h-4 w-4" /><span className="hidden sm:inline">Filter</span></button></div></header>
    <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><MetricCard icon={BarChart3} label="Total trades" value={summary.totalTrades.toLocaleString()} detail="+12.4% vs previous period" /><MetricCard icon={TrendingUp} label="Winning trades" value={summary.winningTrades.toLocaleString()} detail="54.8% win rate" tone="text-emerald-500" /><MetricCard icon={TrendingDown} label="Losing trades" value={summary.losingTrades.toLocaleString()} detail="45.2% of all trades" tone="text-rose-500" /><MetricCard icon={Target} label="Loss rate" value={`${summary.lossRate}%`} detail="−3.8% vs previous period" tone="text-amber-500" /></section>
    <section className="grid gap-6 lg:grid-cols-[1.35fr_1fr]"><CommonCauseStats causes={causes} totalLosses={summary.losingTrades} contextFilterPercentage={contextFilterPercentage} /><SuspectedCauseChart data={weeklyDistribution} /></section>
    <RecentTrades trades={recentTrades} />
    <QuickInsight {...insight} />
  </div>;
}