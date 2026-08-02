import { useEffect, useState } from "react";
import { Activity, ArrowLeft, BrainCircuit, CheckCircle2, Clock3, History, LockKeyhole, Pause, Play, RefreshCw, ShieldCheck, Sparkles, XCircle } from "lucide-react";
import { Link } from "react-router";
import { strategyAutoSelectionPreview, strategySelectionHistoryPreview, type StrategyCandidate, type StrategyRecommendation, type StrategySelectionEvent } from "@/data/strategy-auto-selection";

const recommendationTone: Record<StrategyRecommendation, string> = {
  SELECTED: "bg-emerald-500/10 text-emerald-500",
  ELIGIBLE: "bg-sky-500/10 text-sky-500",
  BLOCKED: "bg-rose-500/10 text-rose-500",
};

export function StrategyAutoSelection() {
  const [selectedId, setSelectedId] = useState(strategyAutoSelectionPreview.selectedStrategyId);
  const [lastEvaluated, setLastEvaluated] = useState(strategyAutoSelectionPreview.generatedAt);
  const [simulationRunning, setSimulationRunning] = useState(false);
  const [secondsUntilRefresh, setSecondsUntilRefresh] = useState(10);
  const [selectionHistory, setSelectionHistory] = useState(strategySelectionHistoryPreview);
  const selected = strategyAutoSelectionPreview.candidates.find((candidate) => candidate.id === selectedId)!;

  const runPreviewSelection = (rotate = false) => {
    const eligible = strategyAutoSelectionPreview.candidates.filter((candidate) => candidate.recommendation !== "BLOCKED");
    const currentIndex = eligible.findIndex((candidate) => candidate.id === selectedId);
    const next = rotate ? eligible[(currentIndex + 1) % eligible.length] : [...eligible].sort((left, right) => right.score - left.score)[0];
    const evaluatedAt = new Date().toISOString();
    setSelectedId(next.id);
    setLastEvaluated(evaluatedAt);
    setSelectionHistory((current) => [{ id: `session-${evaluatedAt}`, strategyName: next.name, reason: rotate ? "Preview market interval changed the highest eligible strategy fit." : "Manual preview evaluation selected the highest current fit score.", selectedAt: evaluatedAt }, ...current].slice(0, 6));
  };

  useEffect(() => {
    if (!simulationRunning) return;
    const timer = window.setInterval(() => {
      setSecondsUntilRefresh((current) => {
        if (current > 1) return current - 1;
        runPreviewSelection(true);
        return 10;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [simulationRunning, selectedId]);

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
      <div>
        <Link to="/auto-trade" className="mb-4 inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"><ArrowLeft className="h-3.5 w-3.5" /> Auto Trade</Link>
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><BrainCircuit className="h-4 w-4" /> Strategy intelligence <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] tracking-normal text-amber-500">Preview data</span></div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Auto-selection strategy mode</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Rank strategy candidates against current market context, diagnostic evidence, and risk gates before execution.</p>
      </div>
      <button type="button" onClick={() => runPreviewSelection()} className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"><RefreshCw className="h-4 w-4" /> Re-evaluate preview</button>
    </header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <ContextMetric label="Symbol" value={strategyAutoSelectionPreview.symbol} />
      <ContextMetric label="Market regime" value={strategyAutoSelectionPreview.marketContext.regime} tone="text-emerald-500" />
      <ContextMetric label="HTF trend" value={strategyAutoSelectionPreview.marketContext.trend} />
      <ContextMetric label="Volatility" value={strategyAutoSelectionPreview.marketContext.volatility} />
      <ContextMetric label="Session" value={strategyAutoSelectionPreview.marketContext.session} />
    </section>

    <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-4">
        <article className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5 shadow-sm">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
            <div><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-500"><Sparkles className="h-4 w-4" /> Selected strategy</div><h2 className="mt-2 text-xl font-semibold">{selected.name}</h2><p className="mt-1 text-sm text-muted-foreground">{selected.description}</p></div>
            <div className="shrink-0 text-left sm:text-right"><p className="text-3xl font-semibold text-emerald-500">{selected.score}</p><p className="text-xs text-muted-foreground">selection score / 100</p></div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">{selected.matchedConditions.map((condition) => <span key={condition} className="rounded-full border border-emerald-500/20 bg-background px-2.5 py-1 text-xs">{condition}</span>)}</div>
        </article>

        <div>
          <div className="mb-3 flex items-end justify-between"><div><h2 className="font-semibold">Strategy candidates</h2><p className="text-xs text-muted-foreground">Deterministic preview ranking from market fit and evidence confidence.</p></div><span className="text-xs text-muted-foreground">{strategyAutoSelectionPreview.candidates.length} evaluated</span></div>
          <div className="space-y-3">{strategyAutoSelectionPreview.candidates.map((candidate, index) => <CandidateCard key={candidate.id} candidate={candidate} rank={index + 1} selected={candidate.id === selectedId} />)}</div>
        </div>
      </div>

      <aside className="space-y-5">
        <article className="rounded-xl border bg-card shadow-sm">
          <div className="border-b p-5"><div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-primary" /><h2 className="font-semibold">Selection guardrails</h2></div><p className="mt-1 text-xs text-muted-foreground">Every gate must pass before a strategy is eligible.</p></div>
          <ul className="divide-y">{strategyAutoSelectionPreview.guardrails.map((guardrail) => <li key={guardrail.label} className="flex items-start gap-3 p-4">{guardrail.passed ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />}<div><p className="text-xs font-medium">{guardrail.label}</p><p className="mt-0.5 text-xs text-muted-foreground">{guardrail.value}</p></div></li>)}</ul>
        </article>
        <FixedRiskPanel />
        <article className="rounded-xl border bg-card p-5 shadow-sm"><div className="flex items-center gap-2"><Activity className="h-4 w-4 text-primary" /><h2 className="font-semibold">Evaluation context</h2></div><dl className="mt-4 space-y-3 text-xs"><Meta label="Analysis frames" value={strategyAutoSelectionPreview.analysisTimeframe} /><Meta label="Spread" value={`${strategyAutoSelectionPreview.marketContext.spreadPips.toFixed(1)} pips`} /><Meta label="Last evaluated" value={new Date(lastEvaluated).toLocaleString()} /></dl></article>
        <article className="rounded-xl border bg-card p-5 shadow-sm"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2"><RefreshCw className={`h-4 w-4 text-primary ${simulationRunning ? "animate-spin" : ""}`} /><h2 className="font-semibold">Dynamic simulation</h2></div><span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${simulationRunning ? "bg-emerald-500/10 text-emerald-500" : "bg-muted text-muted-foreground"}`}>{simulationRunning ? "RUNNING" : "PAUSED"}</span></div><p className="mt-2 text-xs text-muted-foreground">Rotate eligible strategies every 10 seconds using preview market changes.</p><div className="mt-4 flex items-center justify-between rounded-lg bg-muted/50 p-3"><span className="text-xs text-muted-foreground">Next evaluation</span><strong className="font-mono text-sm">{secondsUntilRefresh}s</strong></div><button type="button" onClick={() => { setSimulationRunning((current) => !current); setSecondsUntilRefresh(10); }} className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted">{simulationRunning ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}{simulationRunning ? "Pause simulation" : "Start simulation"}</button></article>
        <SelectionHistory events={selectionHistory} />
        <article className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5"><div className="flex gap-3"><Clock3 className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" /><div><h2 className="text-sm font-semibold">Selection preview only</h2><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Re-evaluation updates page state only. It does not activate a strategy, modify Auto Trade settings, or send broker orders.</p></div></div></article>
      </aside>
    </section>
  </div>;
}

function ContextMetric({ label, value, tone = "text-foreground" }: { label: string; value: string; tone?: string }) { return <article className="rounded-xl border bg-card p-4"><p className="text-xs text-muted-foreground">{label}</p><p className={`mt-2 font-mono text-sm font-semibold ${tone}`}>{value}</p></article>; }
function CandidateCard({ candidate, rank, selected }: { candidate: StrategyCandidate; rank: number; selected: boolean }) { return <article className={`rounded-xl border bg-card p-5 shadow-sm ${selected ? "border-emerald-500/40" : ""}`}><div className="flex gap-4"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-xs font-semibold">{rank}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{candidate.name}</h3><span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${recommendationTone[candidate.recommendation]}`}>{selected ? "SELECTED" : candidate.recommendation}</span></div><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{candidate.description}</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><Score label="Market fit score" value={`${candidate.score}/100`} /><Score label="Evidence confidence" value={`${candidate.confidence}%`} /></div>{candidate.blockedBy && <p className="mt-3 rounded-lg bg-rose-500/5 p-2.5 text-xs text-rose-500">Blocked: {candidate.blockedBy}</p>}</div></div></article>; }
function Score({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-muted/50 p-3"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm font-semibold">{value}</p></div>; }
function Meta({ label, value }: { label: string; value: string }) { return <div className="flex items-start justify-between gap-3"><dt className="text-muted-foreground">{label}</dt><dd className="text-right font-medium">{value}</dd></div>; }
function FixedRiskPanel() { const risk = strategyAutoSelectionPreview.fixedRisk; return <article className="rounded-xl border border-sky-500/30 bg-sky-500/5 shadow-sm"><div className="flex items-start justify-between gap-3 border-b border-sky-500/20 p-5"><div className="flex gap-3"><span className="rounded-lg bg-sky-500/10 p-2 text-sky-500"><LockKeyhole className="h-4 w-4" /></span><div><h2 className="font-semibold">Fixed risk management</h2><p className="mt-0.5 text-xs text-muted-foreground">Locked across every strategy rotation.</p></div></div><span className="rounded-full bg-sky-500/10 px-2 py-0.5 text-[10px] font-semibold text-sky-500">LOCKED</span></div><div className="grid grid-cols-2 gap-3 p-5"><RiskMetric label="Risk / trade" value={`${risk.riskPerTradePct}%`} /><RiskMetric label="Daily loss limit" value={`${risk.dailyLossLimitPct}%`} /><RiskMetric label="Max positions" value={String(risk.maxOpenPositions)} /><RiskMetric label="Stop loss" value={risk.stopLossRequired ? "REQUIRED" : "OPTIONAL"} /></div><div className="mx-5 mb-5 rounded-lg border border-sky-500/20 bg-background/70 p-3"><div className="flex items-center justify-between gap-3 text-xs"><span className="text-muted-foreground">Risk profile</span><strong>{risk.profileName}</strong></div><p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">Auto-selection may change the strategy candidate, but it cannot increase exposure or bypass these limits.</p></div></article>; }
function RiskMetric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-background/70 p-3"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-sm font-semibold">{value}</p></div>; }
function SelectionHistory({ events }: { events: StrategySelectionEvent[] }) { return <article className="rounded-xl border bg-card shadow-sm"><div className="flex items-center gap-2 border-b p-5"><History className="h-4 w-4 text-primary" /><h2 className="font-semibold">Selection history</h2></div><ul className="divide-y">{events.map((event) => <li key={event.id} className="p-4"><div className="flex items-start justify-between gap-3"><p className="text-xs font-medium">{event.strategyName}</p><time className="shrink-0 text-[9px] text-muted-foreground">{new Date(event.selectedAt).toLocaleTimeString()}</time></div><p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{event.reason}</p></li>)}</ul></article>; }