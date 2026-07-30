import { Lightbulb } from "lucide-react";

interface QuickInsightProps {
  cause: string;
  percentage: number;
  recommendation: string;
}

export function QuickInsight({ cause, percentage, recommendation }: QuickInsightProps) {
  return (
    <aside className="flex items-start gap-3 rounded-xl border border-primary/20 bg-primary/5 p-5" aria-labelledby="quick-insight-title">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10">
        <Lightbulb className="h-5 w-5 text-primary" aria-hidden="true" />
      </span>
      <div>
        <h2 id="quick-insight-title" className="font-semibold">Quick insight</h2>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
          {cause} account for <strong className="text-foreground">{percentage}% of your losses</strong>. {recommendation}
        </p>
      </div>
    </aside>
  );
}