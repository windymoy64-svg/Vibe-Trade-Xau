import { Activity, CheckCircle2, FileText, FlaskConical } from "lucide-react";
import { Link } from "react-router";
import type { ImprovementActivity, ImprovementActivityType } from "@/data/diagnostic-improvements";

const activityMeta: Record<ImprovementActivityType, { icon: typeof Activity; color: string }> = {
  NOTE: { icon: FileText, color: "text-muted-foreground bg-muted" },
  STATUS_CHANGE: { icon: CheckCircle2, color: "text-emerald-500 bg-emerald-500/10" },
  EVIDENCE: { icon: FlaskConical, color: "text-sky-500 bg-sky-500/10" },
};

export function ImprovementActivityLog({ activities }: { activities: ImprovementActivity[] }) {
  const orderedActivities = [...activities].sort((left, right) => Date.parse(right.occurredAt) - Date.parse(left.occurredAt));
  return <section aria-labelledby="improvement-activity-title" className="rounded-xl border bg-card p-5 shadow-sm">
    <div className="flex items-start justify-between gap-3"><div><div className="flex items-center gap-2"><Activity className="h-4 w-4 text-primary" /><h2 id="improvement-activity-title" className="font-semibold">Activity log</h2></div><p className="mt-1 text-xs text-muted-foreground">Recent notes and evidence updates for tracked improvements.</p></div><span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">Preview data</span></div>
    {orderedActivities.length === 0 ? <div className="mt-5 rounded-lg border border-dashed p-8 text-center text-xs text-muted-foreground">No activity recorded for the current validation cycle.</div> : <ul className="mt-5 divide-y">
      {orderedActivities.map((activity) => {
        const meta = activityMeta[activity.type];
        const Icon = meta.icon;
        return <li key={activity.id} className="flex gap-3 py-3 first:pt-0 last:pb-0"><span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${meta.color}`}><Icon className="h-4 w-4" /></span><div className="min-w-0 flex-1"><p className="text-xs leading-relaxed text-foreground">{activity.message}</p><div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-muted-foreground"><span>{new Date(activity.occurredAt).toLocaleString()}</span><span aria-hidden="true">·</span><span>{activity.actor}</span><Link to={`/diagnostics/recommendations/${activity.recommendationId}`} className="text-primary hover:underline">View recommendation</Link></div></div></li>;
      })}
    </ul>}
  </section>;
}