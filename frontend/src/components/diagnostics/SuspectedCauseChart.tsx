export interface CauseDistributionPoint {
  label: string;
  wins: number;
  losses: number;
}

interface SuspectedCauseChartProps {
  data: CauseDistributionPoint[];
}

export function SuspectedCauseChart({ data }: SuspectedCauseChartProps) {
  const maximum = Math.max(1, ...data.flatMap((point) => [point.wins, point.losses]));

  return (
    <section className="rounded-xl border bg-card p-5 shadow-sm" aria-labelledby="cause-distribution-title">
      <h2 id="cause-distribution-title" className="font-semibold">Suspected cause distribution</h2>
      <p className="mt-1 text-xs text-muted-foreground">Win and loss count by week</p>

      <div className="mt-8 min-w-[320px] overflow-x-auto"><div className="flex h-40 items-end justify-around gap-3 border-b border-l p-3" role="img" aria-label="Weekly wins and losses bar chart">
        {data.map((point) => (
          <div key={point.label} className="group relative flex h-full flex-1 items-end gap-1" title={`${point.label}: ${point.wins} wins, ${point.losses} losses`}>
            <div className="w-1/2 rounded-t bg-emerald-500/80 transition-opacity group-hover:opacity-70" style={{ height: `${(point.wins / maximum) * 100}%` }} />
            <div className="w-1/2 rounded-t bg-rose-500/70 transition-opacity group-hover:opacity-70" style={{ height: `${(point.losses / maximum) * 100}%` }} />
            <span className="sr-only">{point.label}: {point.wins} wins and {point.losses} losses</span>
          </div>
        ))}
      </div></div>

      <div className="mt-3 flex justify-center gap-5 text-xs text-muted-foreground">
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-500" />Wins</span>
        <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-rose-500" />Losses</span>
      </div>
    </section>
  );
}