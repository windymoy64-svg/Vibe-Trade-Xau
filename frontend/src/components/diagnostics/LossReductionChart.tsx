import { TrendingDown } from "lucide-react";
import type { LossReductionPoint } from "@/data/diagnostic-improvements";

const WIDTH = 640;
const HEIGHT = 220;
const PADDING_X = 36;
const PADDING_Y = 24;

export function LossReductionChart({ data }: { data: LossReductionPoint[] }) {
  if (data.length < 2) {
    return <div className="rounded-lg border border-dashed p-8 text-center"><TrendingDown className="mx-auto h-6 w-6 text-muted-foreground" /><p className="mt-3 text-sm font-medium">Not enough validation data</p><p className="mt-1 text-xs text-muted-foreground">At least two measured periods are required to chart loss reduction.</p></div>;
  }

  const rates = data.map((point) => point.lossRate);
  const minimum = Math.max(0, Math.floor(Math.min(...rates) - 5));
  const maximum = Math.ceil(Math.max(...rates) + 5);
  const range = Math.max(1, maximum - minimum);
  const stepX = (WIDTH - PADDING_X * 2) / (data.length - 1);
  const coordinates = data.map((point, index) => ({
    ...point,
    x: PADDING_X + index * stepX,
    y: PADDING_Y + ((maximum - point.lossRate) / range) * (HEIGHT - PADDING_Y * 2),
  }));
  const line = coordinates.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${PADDING_X},${HEIGHT - PADDING_Y} ${line} ${WIDTH - PADDING_X},${HEIGHT - PADDING_Y}`;
  const baseline = data[0].lossRate;
  const latest = data[data.length - 1].lossRate;
  const delta = Math.round((latest - baseline) * 10) / 10;
  const chartLabel = `Loss rate decreased from ${baseline}% at ${data[0].label} to ${latest}% at ${data[data.length - 1].label}`;

  return <section className="rounded-xl border bg-card p-5 shadow-sm" aria-labelledby="loss-reduction-title">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h2 id="loss-reduction-title" className="font-semibold">Loss reduction</h2><p className="mt-1 text-xs text-muted-foreground">Observed loss rate after controlled strategy changes</p></div>
      <div className="rounded-lg bg-emerald-500/10 px-3 py-2 text-right"><p className="text-[9px] font-semibold uppercase tracking-wide text-emerald-600 dark:text-emerald-400">Change from baseline</p><p className="mt-0.5 font-mono text-lg font-semibold text-emerald-500">{delta > 0 ? "+" : ""}{delta} pp</p></div>
    </div>
    <div className="mt-5 overflow-x-auto">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-[220px] min-w-[560px] w-full" role="img" aria-label={chartLabel}>
        <defs><linearGradient id="loss-reduction-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="rgb(16 185 129)" stopOpacity="0.22" /><stop offset="100%" stopColor="rgb(16 185 129)" stopOpacity="0.01" /></linearGradient></defs>
        {[0, 0.5, 1].map((position) => {
          const y = PADDING_Y + position * (HEIGHT - PADDING_Y * 2);
          const value = maximum - position * range;
          return <g key={position}><line x1={PADDING_X} y1={y} x2={WIDTH - PADDING_X} y2={y} stroke="currentColor" className="text-border" strokeDasharray="4 4" /><text x={PADDING_X - 8} y={y + 3} textAnchor="end" className="fill-muted-foreground text-[9px]">{value.toFixed(0)}%</text></g>;
        })}
        <polygon points={area} fill="url(#loss-reduction-area)" />
        <polyline points={line} fill="none" stroke="rgb(16 185 129)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {coordinates.map((point) => <g key={point.label}><circle cx={point.x} cy={point.y} r="5" fill="rgb(16 185 129)" stroke="currentColor" strokeWidth="3" className="text-card"><title>{point.label}: {point.lossRate}% loss rate across {point.tradeCount} trades</title></circle><text x={point.x} y={HEIGHT - 5} textAnchor="middle" className="fill-muted-foreground text-[9px]">{point.label}</text></g>)}
      </svg>
    </div>
    <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-[10px] text-muted-foreground"><span>{data.reduce((total, point) => total + point.tradeCount, 0).toLocaleString()} measured trades</span><span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-emerald-500" />Loss rate</span></div>
  </section>;
}