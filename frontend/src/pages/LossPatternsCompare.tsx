import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowDownRight, ArrowLeft, ArrowUpRight, CalendarRange, Loader2, Minus } from "lucide-react";
import { Link } from "react-router";
import { lossPatternAnalysisStub, type LossPatternAnalysisData } from "@/data/loss-patterns";
import { api } from "@/lib/api";

const periodLabels = {
  previous_month: "Previous month",
  previous_quarter: "Previous quarter",
  baseline: "Strategy baseline",
} as const;

type ComparisonPeriod = keyof typeof periodLabels;

export function LossPatternsCompare() {
  const [analysis, setAnalysis] = useState<LossPatternAnalysisData>(lossPatternAnalysisStub);
  const [usingPreviewData, setUsingPreviewData] = useState(true);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState<ComparisonPeriod>("previous_month");

  useEffect(() => {
    let active = true;
    api.getLossPatterns()
      .then((data) => {
        if (!active) return;
        setAnalysis(data);
        setUsingPreviewData(false);
      })
      .catch(() => {
        if (!active) return;
        setAnalysis(lossPatternAnalysisStub);
        setUsingPreviewData(true);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const totals = useMemo(() => {
    const improving = analysis.patterns.filter((pattern) => (pattern.trendDelta ?? 0) < 0).length;
    const worsening = analysis.patterns.filter((pattern) => (pattern.trendDelta ?? 0) > 0).length;
    return { improving, worsening, stable: analysis.patterns.length - improving - worsening };
  }, [analysis.patterns]);

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header>
      <Link to="/diagnostics/patterns" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Loss patterns</Link>
      <div className="mt-4 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><CalendarRange className="h-4 w-4" /> Period comparison {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : usingPreviewData ? <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">Preview data</span> : null}</div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Compare loss patterns</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Track whether recurring failure conditions are improving or worsening before changing strategy controls.</p>
        </div>
        <label className="text-xs font-medium text-muted-foreground">Compare current period with
          <select value={period} onChange={(event) => setPeriod(event.target.value as ComparisonPeriod)} className="mt-1 block w-full rounded-lg border bg-card px-3 py-2 text-sm text-foreground outline-none focus:ring-2 focus:ring-primary/30">
            {Object.entries(periodLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
      </div>
    </header>

    <section className="grid gap-3 sm:grid-cols-3">
      <SummaryCard label="Improving patterns" value={totals.improving} tone="text-emerald-500" icon={<ArrowDownRight className="h-4 w-4" />} />
      <SummaryCard label="Worsening patterns" value={totals.worsening} tone="text-rose-500" icon={<ArrowUpRight className="h-4 w-4" />} />
      <SummaryCard label="Stable patterns" value={totals.stable} tone="text-muted-foreground" icon={<Minus className="h-4 w-4" />} />
    </section>

    <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
      <div className="border-b px-5 py-4">
        <h2 className="font-semibold">Current period vs {periodLabels[period].toLowerCase()}</h2>
        <p className="mt-1 text-xs text-muted-foreground">A negative share change means fewer classified losses are attributed to that pattern.</p>
      </div>
      {analysis.patterns.length === 0 ? <div className="p-10 text-center text-sm text-muted-foreground">No patterns are available for comparison yet.</div> : <div className="divide-y">
        {analysis.patterns.map((pattern) => {
          const trendDelta = pattern.trendDelta ?? 0;
          const priorShare = Math.max(0, pattern.lossPercentage - trendDelta);
          const improving = trendDelta < 0;
          const stable = trendDelta === 0;
          return <article key={pattern.id} className="grid gap-4 p-5 sm:grid-cols-[minmax(0,1fr)_120px_120px_130px] sm:items-center">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2"><h3 className="font-medium">{pattern.name}</h3><span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">{pattern.category}</span></div>
              <p className="mt-1 truncate text-xs text-muted-foreground">{pattern.description}</p>
            </div>
            <Metric label="Current share" value={`${pattern.lossPercentage}%`} />
            <Metric label={periodLabels[period]} value={`${priorShare}%`} />
            <div className={`flex items-center gap-2 sm:justify-end ${stable ? "text-muted-foreground" : improving ? "text-emerald-500" : "text-rose-500"}`}>
              {stable ? <Minus className="h-4 w-4" /> : improving ? <ArrowDownRight className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}
              <div><p className="font-mono text-sm font-semibold">{trendDelta > 0 ? "+" : ""}{trendDelta} pp</p><p className="text-[10px] uppercase tracking-wide">{stable ? "Stable" : improving ? "Improving" : "Worsening"}</p></div>
            </div>
          </article>;
        })}
      </div>}
    </section>
  </div>;
}

function SummaryCard({ label, value, tone, icon }: { label: string; value: number; tone: string; icon: ReactNode }) {
  return <div className="rounded-xl border bg-card p-5"><div className="flex justify-between text-xs text-muted-foreground"><span>{label}</span><span className={tone}>{icon}</span></div><p className={`mt-3 text-3xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">of the detected patterns</p></div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm font-semibold">{value}</p></div>;
}