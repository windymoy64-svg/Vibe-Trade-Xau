import { useState } from "react";
import { AlertTriangle, ArrowLeft, RefreshCw, Scale, ShieldAlert } from "lucide-react";
import { Link } from "react-router";

type ReconciliationStatus = "MATCH" | "MISMATCH" | "MISSING_ENGINE" | "MISSING_MT5";
type ReconciliationRow = {
  id: string;
  ticket: string;
  terminal: string;
  status: ReconciliationStatus;
  engine: { side: string; volume: number; entry: number; sl: number; tp: number } | null;
  mt5: { side: string; volume: number; entry: number; sl: number; tp: number } | null;
  difference: string;
};

const initialRows: ReconciliationRow[] = [
  { id: "rec-1", ticket: "ticket-99712", terminal: "EA Terminal A", status: "MATCH", engine: { side: "BUY", volume: 0.05, entry: 2384.25, sl: 2378.25, tp: 2396.25 }, mt5: { side: "BUY", volume: 0.05, entry: 2384.25, sl: 2378.25, tp: 2396.25 }, difference: "All fields match" },
  { id: "rec-2", ticket: "ticket-99718", terminal: "EA Alpari-ECN", status: "MISMATCH", engine: { side: "SELL", volume: 0.03, entry: 2392.1, sl: 2398.1, tp: 2380.1 }, mt5: { side: "SELL", volume: 0.03, entry: 2392.1, sl: 2397.6, tp: 2380.1 }, difference: "Stop loss differs by 0.50" },
  { id: "rec-3", ticket: "ticket-99802", terminal: "EA Terminal A", status: "MISSING_ENGINE", engine: null, mt5: { side: "BUY", volume: 0.01, entry: 2388.5, sl: 2383.5, tp: 2398.5 }, difference: "Position exists in MT5 but not the engine" },
  { id: "rec-4", ticket: "ticket-99811", terminal: "EA VPS Replication", status: "MISSING_MT5", engine: { side: "SELL", volume: 0.02, entry: 2391.4, sl: 2396.4, tp: 2381.4 }, mt5: null, difference: "Position exists in engine but not MT5" },
];

const statusTone: Record<ReconciliationStatus, string> = {
  MATCH: "bg-emerald-500/10 text-emerald-500",
  MISMATCH: "bg-amber-500/10 text-amber-500",
  MISSING_ENGINE: "bg-rose-500/10 text-rose-500",
  MISSING_MT5: "bg-rose-500/10 text-rose-500",
};

export function EaBridgeReconciliation() {
  const [rows, setRows] = useState(initialRows);
  const [lastCheckedAt, setLastCheckedAt] = useState("2026-08-03T08:42:10Z");
  const [message, setMessage] = useState("");
  const exceptions = rows.filter((row) => row.status !== "MATCH");

  const checkNow = () => {
    setLastCheckedAt(new Date().toISOString());
    setMessage("Preview reconciliation refreshed from page-memory snapshots. No MT5 state was modified.");
  };
  const stageResolution = (id: string) => {
    const target = rows.find((row) => row.id === id);
    if (!target) return;
    setRows((current) => current.map((row) => row.id === id ? { ...row, status: "MATCH", difference: "Resolution staged in preview" } : row));
    setMessage(`${target.ticket} resolution staged. Operator approval and backend reconciliation are still required.`);
  };

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end"><div><Link to="/ea-bridge" className="mb-4 inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"><ArrowLeft className="h-3.5 w-3.5" /> EA Bridge</Link><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><Scale className="h-4 w-4" /> State reconciliation</div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Dashboard vs MT5 positions</h1><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Compare engine state to the terminal source of truth and isolate volume, protection, or lifecycle discrepancies.</p></div><button type="button" onClick={checkNow} className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"><RefreshCw className="h-4 w-4" /> Reconcile now</button></header>

    <section className="grid gap-3 sm:grid-cols-3"><Metric label="Positions compared" value={String(rows.length)} detail={`Checked ${new Date(lastCheckedAt).toLocaleTimeString()}`} /><Metric label="Exact matches" value={String(rows.length - exceptions.length)} detail="Engine and MT5 agree" tone="text-emerald-500" /><Metric label="Exceptions" value={String(exceptions.length)} detail="Operator review required" tone="text-amber-500" /></section>
    {message && <p role="status" className="rounded-lg border border-sky-500/30 bg-sky-500/5 px-4 py-3 text-xs text-sky-600">{message}</p>}
    {exceptions.length > 0 && <section aria-label="Reconciliation warning" className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5"><div className="flex gap-3"><ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" /><div><h2 className="text-sm font-semibold">Execution lock recommended</h2><p className="mt-1 text-xs text-muted-foreground">{exceptions.length} differences remain. New automated orders should stay blocked until terminal and engine state agree.</p></div></div></section>}

    <section aria-label="Position reconciliation results" className="rounded-xl border bg-card shadow-sm"><div className="border-b p-5"><h2 className="font-semibold">Position comparison</h2><p className="mt-0.5 text-xs text-muted-foreground">MT5 remains the source of truth for live exposure.</p></div><div className="divide-y">{rows.map((row) => <article key={row.id} className="grid gap-4 p-5 xl:grid-cols-[180px_1fr_1fr_180px] xl:items-center"><div><div className="flex flex-wrap items-center gap-2"><p className="font-mono text-xs font-semibold">{row.ticket}</p><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${statusTone[row.status]}`}>{row.status}</span></div><p className="mt-1 text-[10px] text-muted-foreground">{row.terminal}</p></div><Snapshot label="Dashboard engine" value={row.engine} /><Snapshot label="MT5 terminal" value={row.mt5} /><div><p className={`text-xs ${row.status === "MATCH" ? "text-emerald-500" : "text-amber-600"}`}>{row.difference}</p>{row.status !== "MATCH" && <button type="button" onClick={() => stageResolution(row.id)} className="mt-2 inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[10px] font-medium hover:bg-muted"><RefreshCw className="h-3 w-3" /> Stage resolution</button>}</div></article>)}</div></section>

    <p className="flex items-center gap-2 text-[10px] text-muted-foreground"><AlertTriangle className="h-3.5 w-3.5" /> Preview actions never overwrite MT5 positions or engine state.</p>
  </div>;
}

function Snapshot({ label, value }: { label: string; value: ReconciliationRow["engine"] }) {
  return <div className="rounded-lg border bg-muted/20 p-3"><p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p>{value ? <div className="mt-2 grid grid-cols-5 gap-2 font-mono text-[10px]"><span>{value.side}</span><span>{value.volume.toFixed(2)} lot</span><span>{value.entry.toFixed(2)}</span><span className="text-rose-500">SL {value.sl.toFixed(2)}</span><span className="text-emerald-500">TP {value.tp.toFixed(2)}</span></div> : <p className="mt-2 text-xs text-rose-500">Missing</p>}</div>;
}
function Metric({ label, value, detail, tone = "text-foreground" }: { label: string; value: string; detail: string; tone?: string }) { return <article className="rounded-xl border bg-card p-4"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></article>; }
