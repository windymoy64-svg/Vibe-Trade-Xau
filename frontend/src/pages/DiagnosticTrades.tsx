import { useMemo, useState } from "react";
import { ArrowLeft, ArrowUpRight, Download, FileText, ListFilter, RotateCcw, Search } from "lucide-react";
import { Link } from "react-router";
import { diagnosticTradeListStub, type DiagnosticTradeListItem } from "@/data/diagnostic-trades";

const csvCell = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;

function downloadCsv(trades: DiagnosticTradeListItem[]) {
  const fields: (keyof DiagnosticTradeListItem)[] = ["ticketId", "pair", "entryTime", "direction", "result", "marketRegime", "session", "trendStatus", "emaAlignment", "rsiValue", "atrValue", "volumeStatus", "suspectedReason", "profitLoss"];
  const csv = [fields.join(","), ...trades.map((trade) => fields.map((field) => csvCell(trade[field])).join(","))].join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a"); link.href = url; link.download = "trade-diagnostics.csv"; link.click(); URL.revokeObjectURL(url);
}

function printReport(trades: DiagnosticTradeListItem[]) {
  const popup = window.open("", "_blank", "noopener,noreferrer");
  if (!popup) return;
  const rows = trades.map((trade) => `<tr><td>${trade.ticketId}</td><td>${trade.entryTime}</td><td>${trade.direction}</td><td>${trade.result}</td><td>${trade.marketRegime}</td><td>${trade.suspectedReason ?? "—"}</td><td>${trade.profitLoss.toFixed(2)}</td></tr>`).join("");
  popup.document.write(`<html><head><title>Trade diagnostics</title><style>body{font:14px Arial;padding:32px;color:#111}h1{font-size:22px}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f3f4f6}@media print{button{display:none}}</style></head><body><h1>Trade diagnostic report</h1><p>${trades.length} selected trade(s)</p><table><thead><tr><th>Ticket</th><th>Entry time</th><th>Direction</th><th>Result</th><th>Regime</th><th>Diagnosis</th><th>P/L</th></tr></thead><tbody>${rows}</tbody></table><button onclick="window.print()">Save as PDF / Print</button></body></html>`);
  popup.document.close();
}

export function DiagnosticTrades() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<"ALL" | "TP" | "SL">("ALL");
  const [pair, setPair] = useState("ALL");
  const [session, setSession] = useState("ALL");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return diagnosticTradeListStub.filter((trade) => {
      if (result !== "ALL" && trade.result !== result) return false;
      if (pair !== "ALL" && trade.pair !== pair) return false;
      if (session !== "ALL" && trade.session !== session) return false;
      if (fromDate && trade.entryTime < `${fromDate}T00:00:00Z`) return false;
      if (toDate && trade.entryTime > `${toDate}T23:59:59Z`) return false;
      return !needle || [trade.ticketId, trade.pair, trade.suspectedReason, trade.session, trade.marketRegime].some((value) => value?.toLowerCase().includes(needle));
    });
  }, [fromDate, pair, query, result, session, toDate]);

  const activeFilters = [query, result !== "ALL", pair !== "ALL", session !== "ALL", fromDate, toDate].filter(Boolean).length;
  const resetFilters = () => { setQuery(""); setResult("ALL"); setPair("ALL"); setSession("ALL"); setFromDate(""); setToDate(""); };
  const selectedTrades = diagnosticTradeListStub.filter((trade) => selected.has(trade.id));
  const toggleTrade = (id: string) => setSelected((current) => { const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); return next; });
  const allVisibleSelected = filtered.length > 0 && filtered.every((trade) => selected.has(trade.id));
  const toggleVisible = () => setSelected((current) => { const next = new Set(current); filtered.forEach((trade) => allVisibleSelected ? next.delete(trade.id) : next.add(trade.id)); return next; });

  return <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6 lg:p-8">
    <header><Link to="/diagnostics" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Dashboard</Link><div className="mt-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><ListFilter className="h-4 w-4" /> Trade diagnostics</div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">All trades</h1><p className="mt-1 text-sm text-muted-foreground">Review each entry and its market context diagnosis.</p></div><span className="w-fit rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-600 dark:text-amber-400">Preview data</span></div></header>
    <section className="space-y-3 rounded-xl border bg-card p-4 shadow-sm"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(220px,1fr)_150px_150px]"><label className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search ticket, pair, reason…" className="w-full rounded-lg border bg-background py-2 pl-9 pr-3 text-sm outline-none focus:border-primary" /></label><select value={result} onChange={(event) => setResult(event.target.value as typeof result)} className="rounded-lg border bg-background px-3 py-2 text-sm"><option value="ALL">All results</option><option value="TP">Take profit</option><option value="SL">Stop loss</option></select><select value={pair} onChange={(event) => setPair(event.target.value)} className="rounded-lg border bg-background px-3 py-2 text-sm"><option value="ALL">All pairs</option><option value="XAUUSD">XAUUSD</option></select><select value={session} onChange={(event) => setSession(event.target.value)} className="rounded-lg border bg-background px-3 py-2 text-sm"><option value="ALL">All sessions</option><option value="ASIA">Asia</option><option value="LONDON">London</option><option value="NEW_YORK">New York</option></select><label className="flex items-center gap-2 rounded-lg border bg-background px-3 py-2"><span className="text-xs text-muted-foreground">From</span><input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} className="min-w-0 bg-transparent text-sm outline-none" /></label><label className="flex items-center gap-2 rounded-lg border bg-background px-3 py-2"><span className="text-xs text-muted-foreground">To</span><input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} className="min-w-0 bg-transparent text-sm outline-none" /></label></div><div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3"><span className="text-xs text-muted-foreground">{activeFilters ? `${activeFilters} active filter${activeFilters === 1 ? "" : "s"}` : "All diagnostic trades"}</span>{activeFilters > 0 && <button type="button" onClick={resetFilters} className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"><RotateCcw className="h-3.5 w-3.5" /> Reset filters</button>}</div></section>
    <section className="overflow-hidden rounded-xl border bg-card shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4"><div><h2 className="font-semibold">Trade history</h2><span className="text-xs text-muted-foreground">{filtered.length} trades · {selected.size} selected</span></div><div className="flex gap-2"><button type="button" disabled={!selected.size} onClick={() => downloadCsv(selectedTrades)} className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted disabled:opacity-40"><Download className="h-3.5 w-3.5" /> CSV</button><button type="button" disabled={!selected.size} onClick={() => printReport(selectedTrades)} className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted disabled:opacity-40"><FileText className="h-3.5 w-3.5" /> PDF</button></div></div><div className="overflow-x-auto"><table className="min-w-[940px] w-full text-left text-sm"><thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3"><input type="checkbox" checked={allVisibleSelected} onChange={toggleVisible} aria-label="Select all visible trades" /></th><th className="px-5 py-3">Trade</th><th className="px-5 py-3">Direction</th><th className="px-5 py-3">Result</th><th className="px-5 py-3">Market context</th><th className="px-5 py-3">Diagnosis</th><th className="px-5 py-3 text-right">P/L</th><th className="px-5 py-3" /></tr></thead><tbody className="divide-y">{filtered.map((trade) => <tr key={trade.id} className="hover:bg-muted/30"><td className="px-5 py-4"><input type="checkbox" checked={selected.has(trade.id)} onChange={() => toggleTrade(trade.id)} aria-label={`Select ${trade.ticketId}`} /></td><td className="px-5 py-4"><div className="font-mono text-xs font-medium">#{trade.ticketId}</div><div className="mt-1 text-xs text-muted-foreground">{new Date(trade.entryTime).toLocaleString()}</div></td><td className={`px-5 py-4 text-xs font-semibold ${trade.direction === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>{trade.direction}</td><td className="px-5 py-4"><span className={`rounded-full px-2 py-1 text-xs font-medium ${trade.result === "TP" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>{trade.result}</span></td><td className="px-5 py-4"><div>{trade.marketRegime}</div><div className="mt-1 text-xs text-muted-foreground">{trade.session.replace("_", " ")}</div></td><td className="px-5 py-4 text-muted-foreground">{trade.suspectedReason ?? "No issue detected"}</td><td className={`px-5 py-4 text-right font-mono text-xs font-medium ${trade.profitLoss >= 0 ? "text-emerald-500" : "text-rose-500"}`}>{trade.profitLoss >= 0 ? "+" : "−"}${Math.abs(trade.profitLoss).toFixed(2)}</td><td className="px-5 py-4"><Link to={`/diagnostics/trades/${trade.id}`} aria-label={`View ${trade.ticketId}`} className="inline-flex rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground"><ArrowUpRight className="h-4 w-4" /></Link></td></tr>)}</tbody></table>{filtered.length === 0 && <div className="p-10 text-center text-sm text-muted-foreground">No trades match the current search.</div>}</div></section>
  </div>;
}