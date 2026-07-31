import type { LossPattern } from "@/data/loss-patterns";

type Category = LossPattern["category"];

const CATEGORY_META: Record<Category, { label: string; bar: string; dot: string }> = {
  TREND: { label: "Trend", bar: "bg-rose-500", dot: "bg-rose-500" },
  REGIME: { label: "Regime", bar: "bg-orange-500", dot: "bg-orange-500" },
  SESSION: { label: "Session", bar: "bg-amber-500", dot: "bg-amber-500" },
  MOMENTUM: { label: "Momentum", bar: "bg-sky-500", dot: "bg-sky-500" },
};

interface DominantPatternChartProps {
  patterns: LossPattern[];
}

export function DominantPatternChart({ patterns }: DominantPatternChartProps) {
  if (patterns.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground" role="img" aria-label="No dominant loss patterns to chart">
        No patterns to chart yet.
      </div>
    );
  }

  const ranked = [...patterns].sort((a, b) => b.lossCount - a.lossCount);
  const maxLosses = Math.max(1, ...ranked.map((pattern) => pattern.lossCount));
  const totalLosses = ranked.reduce((sum, pattern) => sum + pattern.lossCount, 0);
  const activeCategories = Array.from(new Set(ranked.map((pattern) => pattern.category)));
  const chartLabel = `Dominant loss pattern chart ranking ${ranked
    .map((pattern) => `${pattern.name} ${pattern.lossCount} losses`)
    .join(", ")}`;

  return (
    <div className="space-y-4">
      <div className="space-y-3.5" role="img" aria-label={chartLabel}>
        {ranked.map((pattern, index) => {
          const meta = CATEGORY_META[pattern.category];
          return (
            <div key={pattern.id} title={`${pattern.name}: ${pattern.lossCount} losses · ${pattern.lossPercentage}% share · ${pattern.confidence}% confidence`}>
              <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
                <span className="flex min-w-0 items-center gap-1.5 font-medium">
                  <span className="font-mono text-[10px] text-muted-foreground">{index + 1}.</span>
                  <span className="truncate">{pattern.name}</span>
                </span>
                <span className="shrink-0 font-mono text-muted-foreground">{pattern.lossCount} losses</span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                <div className={`h-full rounded-full ${meta.bar}`} style={{ width: `${(pattern.lossCount / maxLosses) * 100}%` }} />
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
                <span>{pattern.lossPercentage}% of losses</span>
                <span>{pattern.confidence}% confidence</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between border-t pt-3 text-[10px] text-muted-foreground">
        <span>{totalLosses.toLocaleString()} losses across {ranked.length} patterns</span>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[10px] text-muted-foreground">
        {activeCategories.map((category) => (
          <span key={category} className="flex items-center gap-1.5">
            <i className={`inline-block h-2 w-2 rounded-full ${CATEGORY_META[category].dot}`} />
            {CATEGORY_META[category].label}
          </span>
        ))}
      </div>
    </div>
  );
}
