import { AlertTriangle, CircleHelp } from "lucide-react";

export interface DiagnosticCause {
  label: string;
  percentage: number;
  colorClass: string;
}

interface CommonCauseStatsProps {
  causes: DiagnosticCause[];
  totalLosses: number;
  contextFilterPercentage: number;
}

export function CommonCauseStats({
  causes,
  totalLosses,
  contextFilterPercentage,
}: CommonCauseStatsProps) {
  return (
    <section className="rounded-xl border bg-card p-5 shadow-sm" aria-labelledby="common-loss-causes-title">
      <div className="flex items-start justify-between">
        <div>
          <h2 id="common-loss-causes-title" className="font-semibold">Common loss causes</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Distribution of suspected reasons across {totalLosses.toLocaleString()} losses
          </p>
        </div>
        <CircleHelp className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
      </div>

      <div className="mt-6 space-y-5">
        {causes.map((cause) => (
          <div key={cause.label}>
            <div className="mb-2 flex justify-between text-sm">
              <span>{cause.label}</span>
              <span className="font-mono font-medium">{cause.percentage}%</span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full bg-muted"
              role="progressbar"
              aria-label={cause.label}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={cause.percentage}
            >
              <div
                className={`h-full rounded-full ${cause.colorClass}`}
                style={{ width: `${Math.min(100, Math.max(0, cause.percentage))}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 flex items-center gap-2 rounded-lg bg-amber-500/10 p-3 text-sm text-amber-600 dark:text-amber-400">
        <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>{contextFilterPercentage}% of losses are linked to market context filters.</span>
      </div>
    </section>
  );
}