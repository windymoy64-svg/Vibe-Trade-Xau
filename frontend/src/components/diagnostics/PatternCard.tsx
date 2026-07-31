import { ArrowDown, ArrowUp, ArrowUpRight } from "lucide-react";
import { Link } from "react-router";
import type { LossPattern } from "@/data/loss-patterns";

function severityBadgeClass(severity: LossPattern["severity"]): string {
  if (severity === "HIGH") return "bg-rose-500/10 text-rose-500";
  if (severity === "MEDIUM") return "bg-amber-500/10 text-amber-500";
  return "bg-sky-500/10 text-sky-500";
}

interface PatternCardProps {
  pattern: LossPattern;
  rank: number;
}

export function PatternCard({ pattern, rank }: PatternCardProps) {
  const trend = pattern.trendDelta || 0;
  return <article className="rounded-xl border bg-card p-5 shadow-sm"><div className="flex items-start gap-4"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-sm font-semibold">{rank}</span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold">{pattern.name}</h2><span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{pattern.category}</span><span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${severityBadgeClass(pattern.severity)}`}>{pattern.severity}</span></div><p className="mt-1 text-sm text-muted-foreground">{pattern.description}</p><div className="mt-4 grid grid-cols-4 gap-3"><div><p className="text-[10px] uppercase text-muted-foreground">Losses</p><p className="mt-1 font-mono text-sm font-semibold">{pattern.lossCount.toLocaleString()}</p></div><div><p className="text-[10px] uppercase text-muted-foreground">Share</p><p className="mt-1 font-mono text-sm font-semibold">{pattern.lossPercentage}%</p></div><div><p className="text-[10px] uppercase text-muted-foreground">Confidence</p><p className="mt-1 font-mono text-sm font-semibold">{pattern.confidence}%</p></div><div><p className="text-[10px] uppercase text-muted-foreground">Trend</p><p className={`mt-1 flex items-center gap-0.5 font-mono text-sm font-semibold ${trend > 0 ? "text-rose-500" : trend < 0 ? "text-emerald-500" : "text-muted-foreground"}`}>{trend > 0 ? <ArrowUp className="h-3 w-3" /> : trend < 0 ? <ArrowDown className="h-3 w-3" /> : null}{Math.abs(trend)}%</p></div></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${pattern.lossPercentage}%` }} /></div><div className="mt-3 flex flex-wrap items-center gap-1.5 font-mono text-[10px]"><span className="text-[10px] uppercase text-muted-foreground">Evidence</span>{pattern.evidenceTradeIds.map((tradeId) => <Link key={tradeId} to={`/diagnostics/trades/${tradeId}`} className="rounded-full border bg-muted/50 px-2 py-0.5 text-muted-foreground hover:bg-muted hover:text-foreground">{tradeId.replace("trade_", "#XAU-")}</Link>)}</div></div><Link to={`/diagnostics/trades?reason=${encodeURIComponent(pattern.name)}`} className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label={`View ${pattern.name} trades`}><ArrowUpRight className="h-4 w-4" /></Link></div></article>;
}