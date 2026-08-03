import { useDeferredValue, useState } from "react";
import { ArrowRight, Search, Stethoscope } from "lucide-react";
import { Link } from "react-router";
import type { Mt5DirectPreviewData } from "@/data/mt5-direct";

const fieldClass = "rounded-lg border bg-background px-3 py-2 text-xs outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";

export function Mt5DiagnosticTradeList({ trades }: { trades: Mt5DirectPreviewData["trades"] }) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<"ALL" | "TP" | "SL">("ALL");
  const [session, setSession] = useState("ALL");
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());
  const sessions = [...new Set(trades.map((trade) => trade.session))];
  const visible = trades.filter((trade) => {
    const searchText = `${trade.ticket} ${trade.cause} ${trade.regime}`.toLowerCase();
    return (!deferredQuery || searchText.includes(deferredQuery)) && (result === "ALL" || trade.result === result) && (session === "ALL" || trade.session === session);
  });

  return (
    <section aria-label="MT5 diagnostic trade list" className="rounded-xl border bg-card shadow-sm">
      <header className="flex flex-col justify-between gap-3 border-b p-5 lg:flex-row lg:items-center"><div className="flex items-start gap-3"><span className="rounded-lg bg-primary/10 p-2 text-primary"><Stethoscope className="h-4 w-4" /></span><div><h2 className="font-semibold">Diagnostic trades</h2><p className="mt-0.5 text-xs text-muted-foreground">MT5 execution records enriched with market context at entry.</p></div></div><div className="grid gap-2 sm:grid-cols-[minmax(180px,1fr)_110px_130px]"><label className="relative"><span className="sr-only">Search MT5 diagnostic trades</span><Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" /><input aria-label="Search MT5 diagnostic trades" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ticket or diagnosis..." className={`${fieldClass} w-full pl-9`} /></label><select aria-label="Filter trade result" value={result} onChange={(event) => setResult(event.target.value as "ALL" | "TP" | "SL")} className={fieldClass}><option value="ALL">All results</option><option value="TP">TP</option><option value="SL">SL</option></select><select aria-label="Filter trade session" value={session} onChange={(event) => setSession(event.target.value)} className={fieldClass}><option value="ALL">All sessions</option>{sessions.map((item) => <option key={item}>{item}</option>)}</select></div></header>
      {visible.length === 0 ? <p className="p-8 text-center text-sm text-muted-foreground">No diagnostic trades match the current filters.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-xs"><thead><tr className="border-b text-muted-foreground"><th className="px-5 py-2.5 font-medium">Ticket</th><th className="px-3 py-2.5 font-medium">Side</th><th className="px-3 py-2.5 font-medium">Result</th><th className="px-3 py-2.5 font-medium">Regime / session</th><th className="px-3 py-2.5 font-medium">Diagnosis</th><th className="px-3 py-2.5 font-medium">Evidence</th><th className="px-5 py-2.5 text-right font-medium">Detail</th></tr></thead><tbody>{visible.map((trade) => <tr key={trade.id} className="border-b last:border-0"><td className="px-5 py-3"><p className="font-mono font-semibold">{trade.ticket}</p><p className="mt-0.5 text-[9px] text-muted-foreground">{new Date(trade.analyzedAt).toLocaleString()}</p></td><td className={`px-3 py-3 font-mono font-semibold ${trade.direction === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>{trade.direction}</td><td className="px-3 py-3"><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${trade.result === "TP" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>{trade.result}</span></td><td className="px-3 py-3"><p>{trade.regime}</p><p className="mt-0.5 text-[10px] text-muted-foreground">{trade.session}</p></td><td className="px-3 py-3">{trade.cause}</td><td className="px-3 py-3"><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${trade.confidence >= 90 ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"}`}>{trade.confidence}% COMPLETE</span></td><td className="px-5 py-3 text-right"><Link to={trade.id === "trade-841" ? "/ea-bridge/trades/ea-trade-1840" : `/diagnostics/trades/${trade.id}`} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">Inspect <ArrowRight className="h-3.5 w-3.5" /></Link></td></tr>)}</tbody></table></div>}
      <div className="border-t px-5 py-3 text-xs text-muted-foreground">Showing {visible.length} of {trades.length} production trades.</div>
    </section>
  );
}
