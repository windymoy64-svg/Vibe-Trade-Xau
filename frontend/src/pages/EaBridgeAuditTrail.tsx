import { useDeferredValue, useState } from "react";
import { ArrowLeft, CheckCircle2, FileClock, Search, ShieldCheck } from "lucide-react";
import { Link } from "react-router";
import { eaBridgePreview } from "@/data/ea-bridge";

type AuditLevel = "INFO" | "WARNING" | "ERROR";
type AuditEvent = { id: string; level: AuditLevel; source: string; action: string; status: string; detail: string; timestamp: string; correlationId: string };

const commandEvents: AuditEvent[] = eaBridgePreview.commands.map((command) => ({
  id: command.id,
  level: command.status === "REJECTED" ? "ERROR" : "INFO",
  source: "precision-engine",
  action: command.action,
  status: command.status,
  detail: `${command.type} ${command.volume.toFixed(3)} ${command.symbol} at ${command.price.toFixed(2)} · ${command.latencyMs}ms`,
  timestamp: command.timestamp,
  correlationId: `corr-${command.id}`,
}));

const logEvents: AuditEvent[] = eaBridgePreview.logs.map((log) => ({
  id: log.id,
  level: log.level,
  source: log.source,
  action: "BRIDGE_EVENT",
  status: log.level === "ERROR" ? "FAILED" : "RECORDED",
  detail: log.message,
  timestamp: log.timestamp,
  correlationId: `corr-${log.id}`,
}));

const auditEvents = [...commandEvents, ...logEvents].sort((a, b) => b.timestamp.localeCompare(a.timestamp));
const fieldClass = "rounded-lg border bg-background px-3 py-2 text-xs outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";

export function EaBridgeAuditTrail() {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<"ALL" | AuditLevel>("ALL");
  const [source, setSource] = useState("ALL");
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const sources = [...new Set(auditEvents.map((event) => event.source))];
  const visible = auditEvents.filter((event) => {
    const matchesQuery = !deferredQuery || `${event.action} ${event.detail} ${event.correlationId}`.toLowerCase().includes(deferredQuery);
    return matchesQuery && (level === "ALL" || event.level === level) && (source === "ALL" || event.source === source);
  });

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><Link to="/ea-bridge" className="mb-4 inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"><ArrowLeft className="h-3.5 w-3.5" /> EA Bridge</Link><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><FileClock className="h-4 w-4" /> Immutable event view</div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">EA audit trail</h1><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Trace every command, MT5 acknowledgement, synchronization event, and bridge incident by timestamp and correlation ID.</p></div><span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/5 px-3 py-1.5 text-xs font-semibold text-emerald-500"><ShieldCheck className="h-4 w-4" /> Append-only preview</span></header>

    <section className="grid gap-3 sm:grid-cols-3"><Metric label="Recorded events" value={String(auditEvents.length)} detail="Current preview window" /><Metric label="Acknowledged commands" value={String(eaBridgePreview.commands.filter((command) => command.status === "ACKED" || command.status === "EXECUTED").length)} detail="MT5 response received" tone="text-emerald-500" /><Metric label="Exceptions" value={String(auditEvents.filter((event) => event.level === "ERROR").length)} detail="Requires operator review" tone="text-rose-500" /></section>

    <section aria-label="Audit trail filters" className="grid gap-3 rounded-xl border bg-card p-4 sm:grid-cols-[minmax(220px,1fr)_180px_220px]"><label className="relative"><span className="sr-only">Search audit events</span><Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" /><input aria-label="Search audit events" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Action, message, correlation ID..." className={`${fieldClass} w-full pl-9`} /></label><select aria-label="Filter audit level" value={level} onChange={(event) => setLevel(event.target.value as "ALL" | AuditLevel)} className={fieldClass}><option value="ALL">All levels</option><option value="INFO">Info</option><option value="WARNING">Warning</option><option value="ERROR">Error</option></select><select aria-label="Filter audit source" value={source} onChange={(event) => setSource(event.target.value)} className={fieldClass}><option value="ALL">All sources</option>{sources.map((item) => <option key={item}>{item}</option>)}</select></section>

    <section aria-label="EA audit events" className="rounded-xl border bg-card shadow-sm"><div className="flex items-center justify-between border-b p-5"><div><h2 className="font-semibold">Synchronized event ledger</h2><p className="mt-0.5 text-xs text-muted-foreground">{visible.length} matching events, newest first.</p></div><CheckCircle2 className="h-5 w-5 text-emerald-500" /></div>{visible.length === 0 ? <p className="p-8 text-center text-sm text-muted-foreground">No audit events match the current filters.</p> : <ol className="divide-y">{visible.map((event) => <li key={event.id} className="grid gap-3 p-5 sm:grid-cols-[110px_minmax(0,1fr)_150px] sm:items-start"><div><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${event.level === "ERROR" ? "bg-rose-500/10 text-rose-500" : event.level === "WARNING" ? "bg-amber-500/10 text-amber-500" : "bg-sky-500/10 text-sky-500"}`}>{event.level}</span><p className="mt-2 font-mono text-[10px] text-muted-foreground">{new Date(event.timestamp).toLocaleTimeString()}</p></div><div><div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold">{event.action}</h3><span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground">{event.status}</span></div><p className="mt-1 text-xs text-muted-foreground">{event.detail}</p><p className="mt-2 font-mono text-[9px] text-muted-foreground">{event.correlationId}</p></div><p className="font-mono text-[10px] text-muted-foreground sm:text-right">{event.source}</p></li>)}</ol>}</section>
  </div>;
}

function Metric({ label, value, detail, tone = "text-foreground" }: { label: string; value: string; detail: string; tone?: string }) {
  return <article className="rounded-xl border bg-card p-4"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></article>;
}
