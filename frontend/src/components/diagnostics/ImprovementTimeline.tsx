import { CalendarDays, CheckCircle2, CircleDashed, Clock3, PlayCircle } from "lucide-react";
import { Link } from "react-router";
import type { ImprovementEventStatus, ImprovementTimelineEvent } from "@/data/diagnostic-improvements";

const statusStyle: Record<ImprovementEventStatus, { icon: typeof Clock3; badge: string; dot: string }> = {
  PLANNED: { icon: CircleDashed, badge: "bg-muted text-muted-foreground", dot: "border-muted-foreground/40 bg-background text-muted-foreground" },
  APPLIED: { icon: PlayCircle, badge: "bg-sky-500/10 text-sky-500", dot: "border-sky-500/30 bg-sky-500/10 text-sky-500" },
  MONITORING: { icon: Clock3, badge: "bg-amber-500/10 text-amber-500", dot: "border-amber-500/30 bg-amber-500/10 text-amber-500" },
  VALIDATED: { icon: CheckCircle2, badge: "bg-emerald-500/10 text-emerald-500", dot: "border-emerald-500/30 bg-emerald-500/10 text-emerald-500" },
};

export function ImprovementTimeline({ events }: { events: ImprovementTimelineEvent[] }) {
  const orderedEvents = [...events].sort((left, right) => Date.parse(right.occurredAt) - Date.parse(left.occurredAt));

  if (orderedEvents.length === 0) {
    return <div className="rounded-lg border border-dashed p-8 text-center"><CalendarDays className="mx-auto h-6 w-6 text-muted-foreground" /><p className="mt-3 text-sm font-medium">No improvement activity yet</p><p className="mt-1 text-xs text-muted-foreground">Apply a recommendation to start an evidence timeline.</p></div>;
  }

  return <ol aria-label="Improvement timeline" className="space-y-0">
    {orderedEvents.map((event, index) => {
      const style = statusStyle[event.status];
      const Icon = style.icon;
      return <li key={event.id} className="relative grid grid-cols-[36px_minmax(0,1fr)] gap-3 pb-6 last:pb-0">
        {index < orderedEvents.length - 1 && <span aria-hidden="true" className="absolute bottom-0 left-[17px] top-9 w-px bg-border" />}
        <span className={`relative z-10 flex h-9 w-9 items-center justify-center rounded-full border ${style.dot}`}><Icon className="h-4 w-4" /></span>
        <article className="min-w-0 rounded-lg border bg-background/50 p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0"><h3 className="text-sm font-medium">{event.title}</h3><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{event.description}</p></div>
            <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold tracking-wide ${style.badge}`}>{event.status}</span>
          </div>
          {event.evidenceNote && <p className="mt-3 rounded-md bg-primary/5 px-3 py-2 text-xs text-muted-foreground"><strong className="text-foreground">Evidence:</strong> {event.evidenceNote}</p>}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-[10px] text-muted-foreground">
            <span>{new Date(event.occurredAt).toLocaleString()} · {event.owner}</span>
            <Link to={`/diagnostics/recommendations/${event.recommendationId}`} className="font-medium text-primary hover:underline">View recommendation</Link>
          </div>
        </article>
      </li>;
    })}
  </ol>;
}