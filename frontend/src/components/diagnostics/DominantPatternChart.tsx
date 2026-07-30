import type { LossPattern } from "@/data/loss-patterns";

interface DominantPatternChartProps { patterns: LossPattern[]; }

export function DominantPatternChart({ patterns }: DominantPatternChartProps) {
  const maxLosses = Math.max(1, ...patterns.map((pattern) => pattern.lossCount));
  return <div className="space-y-4" role="img" aria-label="Dominant loss pattern chart">{patterns.map((pattern) => <div key={pattern.id}><div className="mb-1.5 flex items-center justify-between gap-3 text-xs"><span className="truncate font-medium">{pattern.name}</span><span className="shrink-0 font-mono text-muted-foreground">{pattern.lossCount} losses</span></div><div className="flex h-2 gap-1"><div className="rounded-full bg-rose-500" style={{ width: `${(pattern.lossCount / maxLosses) * 100}%` }} /><div className="rounded-full bg-primary/50" style={{ width: `${(pattern.confidence / 100) * 35}%` }} /></div><div className="mt-1 text-[10px] text-muted-foreground">{pattern.lossPercentage}% of losses · {pattern.confidence}% confidence</div></div>)}</div>;
}