import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, ListFilter, Loader2, RefreshCw } from "lucide-react";
import { Link } from "react-router";
import { api } from "@/lib/api";

type Result = "ALL" | "TP" | "SL";

interface DiagnosticTradeRow {
  id: string;
  ticket_id: string;
  pair: string;
  direction: string;
  result: string;
  entry_time: string;
  market_regime: string;
  trading_session: string;
  suspected_reason: string | null;
  profit_loss: number | null;
}

export function DiagnosticTrades() {
  const [trades, setTrades] = useState<DiagnosticTradeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<Result>("ALL");
  const [pair, setPair] = useState("ALL");
  const [session, setSession] = useState("ALL");

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.getDiagnosticTrades(100);
      setTrades(data.items as unknown as DiagnosticTradeRow[]);
      setError(null);
    } catch (value) {
      setError(value instanceof Error ? value.message : "Gagal memuat diagnostic trades");
      setTrades([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return trades.filter((trade) => {
      if (result !== "ALL" && trade.result !== result) return false;
      if (pair !== "ALL" && trade.pair !== pair) return false;
      if (session !== "ALL" && trade.trading_session !== session) return false;
      return !needle || [trade.ticket_id, trade.pair, trade.suspected_reason, trade.trading_session, trade.market_regime].some((value) => value?.toLowerCase().includes(needle));
    });
  }, [query, result, pair, session, trades]);

  return <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6 lg:p-8">
    <header><Link to="/diagnostics" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Dashboard</Link><div className="mt-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><ListFilter className="h-4 w-4" /> Trade diagnostics {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : trades.length ? <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-500">LIVE DATA</span> : <span className="rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] text-rose-500">NO DATA</span>}</div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">All trades</h1><p className="mt-1 text-sm text-muted-foreground">Review each entry and its market context diagnosis.</p></div><button type="button" onClick={() => void load()} className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs"><RefreshCw className="h-3.5 w-3.5" /> Refresh</button></div></header>
    {error && <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3 text-xs text-rose-500">{error}</div>}
    <section className="space-y-3 rounded-xl border bg-card p-4 shadow-sm"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(220px,1fr)_150px_150px]"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search ticket, pair, reason…" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary" /><select value={result} onChange={(event) => setResult(event.target.value as Result)} className="rounded-lg border bg-background px-3 py-2 text-sm"><option value="ALL">All results</option><option value="TP">Take profit</option><option value="SL">Stop loss</option></select><select value={pair} onChange={(event) => setPair(event.target.value)} className="rounded-lg border bg-background px-3 py-2 text-sm"><option value="ALL">All pairs</option><option value="XAUUSD">XAUUSD</option></select><select value={session} onChange={(event) => setSession(event.target.value)} className="rounded-lg border bg-background px-3 py-2 text-sm"><option value="ALL">All sessions</option><option value="ASIA">Asia</option><option value="LONDON">London</option><option value="NEW_YORK">New York</option></select></div></section>
    <section className="overflow-hidden rounded-xl border bg-card shadow-sm"><div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4"><div><h2 className="font-semibold">Trade history</h2><span className="text-xs text-muted-foreground">{filtered.length} trades</span></div></div><div className="overflow-x-auto"><table className="w-full min-w-[940px] text-left text-sm"><thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground"><tr><th className="px-5 py-3">Trade</th><th className="px-5 py-3">Direction</th><th className="px-5 py-3">Result</th><th className="px-5 py-3">Market context</th><th className="px-5 py-3">Diagnosis</th><th className="px-5 py-3 text-right">P/L</th></tr></thead><tbody className="divide-y">{filtered.map((trade) => <tr key={trade.id} className="hover:bg-muted/30"><td className="px-5 py-4"><div className="font-mono text-xs font-medium">#{trade.ticket_id}</div><div className="mt-1 text-xs text-muted-foreground">{new Date(trade.entry_time).toLocaleString()}</div></td><td className="px-5 py-4"><span className={`text-xs font-semibold ${trade.direction === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>{trade.direction}</span></td><td className="px-5 py-4"><span className={`rounded-full px-2 py-1 text-xs font-medium ${trade.result === "TP" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>{trade.result}</span></td><td className="px-5 py-4 text-xs text-muted-foreground">{trade.market_regime || "—"} · {trade.trading_session || "—"}</td><td className="px-5 py-4 text-xs text-muted-foreground">{trade.suspected_reason ?? "—"}</td><td className={`px-5 py-4 text-right font-mono text-xs font-medium ${trade.profit_loss == null ? "text-muted-foreground" : trade.profit_loss >= 0 ? "text-emerald-500" : "text-rose-500"}`}>{trade.profit_loss == null ? "—" : trade.profit_loss.toFixed(2)}</td></tr>)}</tbody></table>{!filtered.length && <p className="p-8 text-center text-sm text-muted-foreground">Belum ada diagnostic trades untuk filter ini.</p>}</div></section>
  </div>;
}
