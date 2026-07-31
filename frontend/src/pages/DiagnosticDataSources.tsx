import { AlertTriangle, ArrowLeft, CheckCircle2, Database, FileUp, Plug, RefreshCw, Unplug, Webhook } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { diagnosticDataSourcesStub, type DiagnosticDataSource, type DiagnosticSourceStatus } from "@/data/diagnostic-data-sources";

const statusStyle: Record<DiagnosticSourceStatus, string> = { CONNECTED: "bg-emerald-500/10 text-emerald-500", AVAILABLE: "bg-muted text-muted-foreground", ATTENTION: "bg-amber-500/10 text-amber-500" };
const sourceIcon = { mt5: Database, csv: FileUp, webhook: Webhook };

export function DiagnosticDataSources() {
  const [sources, setSources] = useState(diagnosticDataSourcesStub);
  const [message, setMessage] = useState<string | null>(null);
  const connected = sources.filter((source) => source.status === "CONNECTED").length;
  const trades = sources.reduce((total, source) => total + source.importedTrades, 0);

  const changeStatus = (id: string, status: DiagnosticSourceStatus) => {
    setSources((current) => current.map((source) => source.id === id ? { ...source, status } : source));
    setMessage("Mock connection state updated for this page session.");
  };

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header><Link to="/diagnostics" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Diagnostic dashboard</Link><div className="mt-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><Plug className="h-4 w-4" /> Evidence ingestion <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">Preview data</span></div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Diagnostic data sources</h1><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Connect trade history and live execution evidence before running diagnostics.</p></div><Link to="/settings" className="text-xs font-medium text-primary hover:underline">Open global data settings</Link></div></header>

    <section className="grid gap-3 sm:grid-cols-3"><Summary label="Connected sources" value={String(connected)} detail={`${sources.length} integrations configured`} /><Summary label="Imported trades" value={trades.toLocaleString()} detail="Across all preview sources" /><Summary label="Required fields" value="8/8" detail="Core diagnostic context covered" tone="text-emerald-500" /></section>
    {message && <p className="flex items-center gap-2 rounded-lg bg-sky-500/10 px-3 py-2 text-xs text-sky-600 dark:text-sky-400"><CheckCircle2 className="h-4 w-4" />{message}</p>}

    <section className="grid gap-4 lg:grid-cols-3">
      {sources.map((source) => <SourceCard key={source.id} source={source} onStatus={changeStatus} />)}
    </section>

    <section className="rounded-xl border bg-card p-5 shadow-sm"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" /><div><h2 className="font-semibold">Preview-only integrations</h2><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Buttons on this page do not open a network connection, upload a file, or persist credentials. Backend connector setup will be implemented separately.</p></div></div></section>
  </div>;
}

function SourceCard({ source, onStatus }: { source: DiagnosticDataSource; onStatus: (id: string, status: DiagnosticSourceStatus) => void }) {
  const Icon = sourceIcon[source.id as keyof typeof sourceIcon] ?? Database;
  const connected = source.status === "CONNECTED";
  return <article className={`rounded-xl border bg-card p-5 shadow-sm ${source.status === "ATTENTION" ? "border-amber-500/30" : ""}`}><div className="flex items-start justify-between gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary"><Icon className="h-5 w-5" /></span><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${statusStyle[source.status]}`}>{source.status}</span></div><p className="mt-4 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{source.type}</p><h2 className="mt-1 font-semibold">{source.name}</h2><p className="mt-2 min-h-12 text-xs leading-relaxed text-muted-foreground">{source.description}</p><div className="mt-4 flex flex-wrap gap-1.5">{source.coverage.map((item) => <span key={item} className="rounded-full bg-muted px-2 py-1 text-[9px] text-muted-foreground">{item}</span>)}</div><dl className="mt-4 grid grid-cols-2 gap-3 border-t pt-4 text-xs"><div><dt className="text-muted-foreground">Imported</dt><dd className="mt-1 font-mono font-semibold">{source.importedTrades.toLocaleString()}</dd></div><div><dt className="text-muted-foreground">Last sync</dt><dd className="mt-1 text-[10px] font-medium">{source.lastSyncAt ? new Date(source.lastSyncAt).toLocaleString() : "Never"}</dd></div></dl><div className="mt-4 flex gap-2">{connected ? <><button type="button" onClick={() => setTimeout(() => onStatus(source.id, "CONNECTED"), 150)} className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted"><RefreshCw className="h-3.5 w-3.5" /> Test</button><button type="button" onClick={() => onStatus(source.id, "AVAILABLE")} className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs text-muted-foreground hover:bg-muted"><Unplug className="h-3.5 w-3.5" /> Disconnect</button></> : <button type="button" onClick={() => onStatus(source.id, "CONNECTED")} className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground"><Plug className="h-3.5 w-3.5" /> Connect mock source</button>}</div></article>;
}

function Summary({ label, value, detail, tone = "text-foreground" }: { label: string; value: string; detail: string; tone?: string }) {
  return <div className="rounded-xl border bg-card p-5"><p className="text-xs text-muted-foreground">{label}</p><p className={`mt-3 text-3xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div>;
}