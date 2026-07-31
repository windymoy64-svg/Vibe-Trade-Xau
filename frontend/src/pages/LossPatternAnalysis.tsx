import { useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, ArrowRightLeft, ArrowUpRight, BrainCircuit, Download, Loader2, ShieldAlert, Target } from "lucide-react";
import { Link } from "react-router";
import { lossPatternAnalysisStub, type LossPattern, type LossPatternAnalysisData } from "@/data/loss-patterns";
import { DominantPatternChart } from "@/components/diagnostics/DominantPatternChart";
import { api } from "@/lib/api";

function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character] ?? character);
}

function printPatternReport(analysis: LossPatternAnalysisData) {
  const popup = window.open("", "_blank", "noopener,noreferrer");
  if (!popup) return;
  const rows = analysis.patterns.map((pattern) => `<tr><td>${escapeHtml(pattern.name)}</td><td>${escapeHtml(pattern.category)}</td><td>${pattern.lossCount}</td><td>${pattern.lossPercentage}%</td><td>${pattern.confidence}%</td><td>${escapeHtml(pattern.severity)}</td></tr>`).join("");
  popup.document.write(`<html><head><title>Loss pattern analysis</title><style>body{font:14px Arial;padding:32px;color:#111}h1{font-size:22px;margin-bottom:4px}.meta{color:#555}.metrics{display:flex;gap:12px;margin:20px 0}.metric{border:1px solid #ddd;border-radius:8px;padding:12px;min-width:140px}.metric strong{display:block;font-size:22px;margin-top:5px}.insight{background:#f3f4f6;border-radius:8px;padding:14px}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f3f4f6}button{margin-top:20px;padding:10px 14px}@media print{button{display:none}}</style></head><body><h1>Loss pattern analysis report</h1><p class="meta">Generated ${escapeHtml(new Date(analysis.generatedAt).toLocaleString())}</p><div class="metrics"><div class="metric">Detected patterns<strong>${analysis.patterns.length}</strong></div><div class="metric">Classified losses<strong>${analysis.summary.lossesClassifiedPct}%</strong></div><div class="metric">Total losses<strong>${analysis.summary.totalLosses}</strong></div></div><p class="insight"><strong>${escapeHtml(analysis.insight.title)}:</strong> ${escapeHtml(analysis.insight.detail)}</p><table><thead><tr><th>Pattern</th><th>Category</th><th>Losses</th><th>Share</th><th>Confidence</th><th>Severity</th></tr></thead><tbody>${rows}</tbody></table><button onclick="window.print()">Save as PDF / Print</button></body></html>`);
  popup.document.close();
}

function severityBadgeClass(severity: LossPattern["severity"]): string {
  if (severity === "HIGH") return "bg-rose-500/10 text-rose-500";
  if (severity === "MEDIUM") return "bg-amber-500/10 text-amber-500";
  return "bg-sky-500/10 text-sky-500";
}

function PatternCard({ pattern, rank }: { pattern: LossPattern; rank: number }) {
  return <article className="rounded-xl border bg-card p-5 shadow-sm">
    <div className="flex items-start gap-4">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-sm font-semibold">{rank}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold">{pattern.name}</h2>
          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{pattern.category}</span>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${severityBadgeClass(pattern.severity)}`}>{pattern.severity}</span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{pattern.description}</p>
        <div className="mt-4 grid grid-cols-3 gap-3">
          <div><p className="text-[10px] uppercase text-muted-foreground">Losses</p><p className="mt-1 font-mono text-sm font-semibold">{pattern.lossCount.toLocaleString()}</p></div>
          <div><p className="text-[10px] uppercase text-muted-foreground">Share</p><p className="mt-1 font-mono text-sm font-semibold">{pattern.lossPercentage}%</p></div>
          <div><p className="text-[10px] uppercase text-muted-foreground">Confidence</p><p className="mt-1 font-mono text-sm font-semibold">{pattern.confidence}%</p></div>
        </div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${pattern.lossPercentage}%` }} /></div>
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] uppercase text-muted-foreground">Evidence</span>
          {pattern.evidenceTradeIds.map((tradeId) => <Link key={tradeId} to={`/diagnostics/trades/${tradeId}`} className="rounded-full border bg-muted/50 px-2 py-0.5 font-mono text-[10px] text-muted-foreground hover:bg-muted hover:text-foreground">{tradeId.replace("trade_", "#XAU-")}</Link>)}
        </div>
      </div>
      <Link to={`/diagnostics/trades?reason=${encodeURIComponent(pattern.name)}`} className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={`View ${pattern.name} trades`}><ArrowUpRight className="h-4 w-4" /></Link>
    </div>
  </article>;
}

export function LossPatternAnalysis() {
  const [analysis, setAnalysis] = useState<LossPatternAnalysisData>(lossPatternAnalysisStub);
  const [usingPreviewData, setUsingPreviewData] = useState(true);
  const [loading, setLoading] = useState(true);

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

  const { summary, patterns, insight, generatedAt } = analysis;
  const detectedPatterns = patterns.length;
  const highSeverityPatterns = patterns.filter((pattern) => pattern.severity === "HIGH").length;

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header>
      <Link to="/diagnostics" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Dashboard</Link>
      <div className="mt-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><BrainCircuit className="h-4 w-4" /> Evidence pattern engine {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : usingPreviewData ? <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">Preview data</span> : null}</div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Loss pattern analysis</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Rank recurring failure conditions before changing strategy parameters.</p>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          <div className="flex flex-wrap gap-2">
            <Link to="/diagnostics/patterns/compare" className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"><ArrowRightLeft className="h-4 w-4" /> Compare periods</Link>
            <button type="button" onClick={() => printPatternReport(analysis)} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90"><Download className="h-4 w-4" /> Export PDF</button>
          </div>
          <p className="w-fit text-xs text-muted-foreground">Generated {new Date(generatedAt).toLocaleString()}</p>
        </div>
      </div>
    </header>
    <section className="grid gap-3 sm:grid-cols-3">
      <div className="rounded-xl border bg-card p-5"><div className="flex justify-between text-xs text-muted-foreground"><span>Detected patterns</span><Target className="h-4 w-4" /></div><p className="mt-3 text-3xl font-semibold">{detectedPatterns}</p><p className="mt-1 text-xs text-muted-foreground">{summary.classifiedLosses.toLocaleString()} of {summary.totalLosses.toLocaleString()} losses clustered</p></div>
      <div className="rounded-xl border bg-card p-5"><div className="flex justify-between text-xs text-muted-foreground"><span>Losses classified</span><ShieldAlert className="h-4 w-4" /></div><p className="mt-3 text-3xl font-semibold">{summary.lossesClassifiedPct}%</p><p className="mt-1 text-xs text-muted-foreground">{summary.classifiedLosses.toLocaleString()} classified losses</p></div>
      <div className="rounded-xl border bg-card p-5"><div className="flex justify-between text-xs text-muted-foreground"><span>High severity</span><AlertTriangle className="h-4 w-4" /></div><p className="mt-3 text-3xl font-semibold text-rose-500">{highSeverityPatterns}</p><p className="mt-1 text-xs text-muted-foreground">Patterns needing immediate controls</p></div>
    </section>
    <section className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <div className="space-y-3">
        {patterns.length === 0 ? <div className="rounded-xl border border-dashed bg-card p-10 text-center text-sm text-muted-foreground">No loss patterns detected yet. Import losing trades to start clustering failure conditions.</div> : patterns.map((pattern, index) => <PatternCard key={pattern.id} pattern={pattern} rank={index + 1} />)}
      </div>
      <aside className="h-fit space-y-6 rounded-xl border bg-card p-5 shadow-sm">
        <div>
          <h2 className="font-semibold">Dominant patterns</h2>
          <p className="mt-1 text-xs text-muted-foreground">Loss count and confidence by pattern</p>
          <div className="mt-5"><DominantPatternChart patterns={patterns} /></div>
        </div>
        <div className="rounded-lg bg-primary/5 p-4 text-xs leading-relaxed text-muted-foreground"><strong className="text-foreground">{insight.title}:</strong> {insight.detail}</div>
      </aside>
    </section>
  </div>;
}