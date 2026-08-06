import { useCallback, useEffect, useState } from "react";
import { Activity, ArrowRight, BarChart3, Bot, Crosshair, Database, Radio, RefreshCw, ShieldCheck, Terminal, Wifi, WifiOff, Zap } from "lucide-react";
import { Link } from "react-router";
import { terminalApi, type AutoSelectionStatus, type AutoTradeRunnerStatus, type Mt5ConnectionStatus, type Mt5LiveSnapshot } from "@/lib/trading-terminal-api";

type LiveState = "LOADING" | "LIVE" | "OFFLINE";

interface HomeData {
  connection: Mt5ConnectionStatus | null;
  snapshot: Mt5LiveSnapshot | null;
  runner: AutoTradeRunnerStatus | null;
  selection: AutoSelectionStatus | null;
}

const initialData: HomeData = { connection: null, snapshot: null, runner: null, selection: null };

export function Home() {
  const [data, setData] = useState<HomeData>(initialData);
  const [state, setState] = useState<LiveState>("LOADING");
  const [lastRefresh, setLastRefresh] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const runner = await Promise.allSettled([terminalApi.runnerStatus()]);
    const runnerValue = runner[0].status === "fulfilled" ? runner[0].value : null;
    const timeframe = runnerValue?.timeframe || "M15";
    const [connection, snapshot, selection] = await Promise.allSettled([
      terminalApi.connection(),
      terminalApi.liveSnapshot("XAUUSD", timeframe),
      terminalApi.selectionStatus("XAUUSD"),
    ]);
    const next: HomeData = {
      connection: connection.status === "fulfilled" ? connection.value : null,
      snapshot: snapshot.status === "fulfilled" ? snapshot.value : null,
      runner: runnerValue,
      selection: selection.status === "fulfilled" ? selection.value : null,
    };
    setData(next);
    setState(next.snapshot?.connected || next.connection?.terminalConnected ? "LIVE" : "OFFLINE");
    setLastRefresh(new Date().toISOString());
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const snapshot = data.snapshot;
  const runner = data.runner;
  const selection = data.selection;
  const quote = snapshot?.quote;
  const latestBar = snapshot?.bars[snapshot.bars.length - 1];
  const latestTick = data.connection?.lastTickTime || (quote?.time ? new Date(quote.time * 1000).toISOString() : null);
  const sourceLabel = state === "LIVE" ? "LIVE MT5" : state === "OFFLINE" ? "OFFLINE" : "CONNECTING";

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
              <BarChart3 className="h-4 w-4" /> Trading command center
              <span className={`rounded-full px-2 py-1 text-[10px] tracking-normal ${state === "LIVE" ? "bg-emerald-400/10 text-emerald-300" : "bg-rose-400/10 text-rose-300"}`}>
                {state === "LIVE" ? <Wifi className="mr-1 inline h-3 w-3" /> : <WifiOff className="mr-1 inline h-3 w-3" />}{sourceLabel}
              </span>
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">XAUUSD operator dashboard</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">Read-only overview of the MT5 market feed, adaptive runner, strategy selection, risk state, and execution context.</p>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>{lastRefresh ? `Updated ${new Date(lastRefresh).toLocaleTimeString()}` : "Waiting for first snapshot"}</span>
            <button type="button" onClick={() => void refresh()} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 font-medium hover:bg-slate-800"><RefreshCw className="h-3.5 w-3.5" /> Refresh</button>
          </div>
        </header>

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Metric label="Bid" value={quote ? quote.bid.toFixed(2) : "--"} detail={snapshot?.symbol || "XAUUSD"} />
          <Metric label="Ask" value={quote ? quote.ask.toFixed(2) : "--"} detail={quote?.spread != null ? `Spread ${quote.spread}` : "Spread unavailable"} />
          <Metric label="Candle" value={latestBar ? latestBar.close.toFixed(2) : "--"} detail={snapshot?.timeframe || "M15"} />
          <Metric label="MT5 connection" value={data.connection?.terminalConnected ? "CONNECTED" : "OFFLINE"} detail={data.connection?.latencyMs != null ? `${data.connection.latencyMs} ms latency` : "No latency snapshot"} tone={data.connection?.terminalConnected ? "text-emerald-300" : "text-rose-300"} />
          <Metric label="Bot runner" value={runner?.running ? "RUNNING" : "STOPPED"} detail={runner?.state || "STATUS UNAVAILABLE"} tone={runner?.running ? "text-amber-300" : "text-slate-300"} />
        </section>

        {state === "OFFLINE" && <div className="flex items-start gap-3 rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-100"><WifiOff className="mt-0.5 h-5 w-5 shrink-0" /><div><p className="font-semibold">Live MT5 data unavailable</p><p className="mt-1 text-xs text-rose-200/80">Home is not showing simulated market data. Start the backend and connect the demo MT5 terminal before trusting market status.</p></div></div>}

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
          <article className="rounded-2xl border border-cyan-400/20 bg-slate-900 p-5 shadow-2xl shadow-cyan-950/20">
            <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">Adaptive decision</p><h2 className="mt-2 text-xl font-semibold">{selection?.selectedStrategyId || runner?.selectedStrategyId || "No live strategy selection"}</h2></div><span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${selection?.status === "READY" ? "bg-emerald-400/10 text-emerald-300" : "bg-slate-800 text-slate-400"}`}>{selection?.status || "UNAVAILABLE"}</span></div>
            <p className="mt-3 text-sm text-slate-300">{selection?.reason || runner?.decisionReason || runner?.message || "The backend has not published an adaptive decision."}</p>
            <div className="mt-5 grid gap-3 sm:grid-cols-4"><Value label="Regime" value={selection?.marketContext.regime || "--"} /><Value label="Trend" value={selection?.marketContext.trend || "--"} /><Value label="Volatility" value={selection?.marketContext.volatility || "--"} /><Value label="Session" value={selection?.marketContext.session || "--"} /></div>
            <div className="mt-4 grid gap-3 sm:grid-cols-4"><Value label="RSI" value={formatNumber(selection?.marketContext.rsi)} /><Value label="ATR" value={formatNumber(selection?.marketContext.atr)} /><Value label="Volume ratio" value={formatNumber(selection?.marketContext.volumeRatio)} /><Value label="Spread pips" value={formatNumber(selection?.marketContext.spreadPips)} /></div>
          </article>
          <article className="rounded-2xl border border-slate-800 bg-slate-900 p-5"><div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-300" /><h2 className="font-semibold">Execution context</h2></div><dl className="mt-5 space-y-3 text-xs"><Row label="Last candle" value={runner?.lastCandleAt ? new Date(runner.lastCandleAt).toLocaleString() : "--"} /><Row label="Decision" value={runner?.lastDecision || "--"} /><Row label="Order type" value={runner?.orderType || "--"} /><Row label="Entry" value={formatNumber(runner?.entryPrice)} /><Row label="Stop loss" value={formatNumber(runner?.stopLoss)} /><Row label="Take profit" value={formatNumber(runner?.takeProfit)} /><Row label="Last order" value={runner?.lastOrderId || "--"} /></dl>{runner?.lastError && <p className="mt-4 rounded-lg border border-rose-400/20 bg-rose-400/10 p-3 text-xs text-rose-200">{runner.lastError}</p>}</article>
        </section>

        <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          <StatusCard icon={Terminal} title="Account" value={snapshot?.account ? `${snapshot.account.is_demo ? "DEMO" : "LIVE"} · ${snapshot.account.server}` : "UNAVAILABLE"} detail={snapshot?.account ? `Equity ${snapshot.account.equity.toFixed(2)} · Free margin ${snapshot.account.margin_free.toFixed(2)}` : "No account snapshot"} />
          <StatusCard icon={Activity} title="Market feed" value={state === "LIVE" ? "HEALTHY" : "UNAVAILABLE"} detail={latestTick ? `Last tick ${new Date(latestTick).toLocaleTimeString()}` : "Last tick unavailable"} />
          <StatusCard icon={Bot} title="Positions / orders" value={`${snapshot?.positions.length || 0} / ${snapshot?.orders.length || data.connection?.pendingOrdersCount || 0}`} detail="Open positions / pending orders" />
          <StatusCard icon={Database} title="Backtest" value="NO RESULT" detail="Backtest dashboard is not connected to a completed adaptive run yet." />
        </section>

        <section><div className="mb-3 flex items-end justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">Operations</p><h2 className="mt-1 text-lg font-semibold">Open a live module</h2></div><span className="text-xs text-slate-500">Monitoring only · controls remain in Auto Trade</span></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><QuickLink to="/auto-trade" icon={Zap} title="Auto Trade" detail="Runner controls and execution logs" /><QuickLink to="/auto-trade/strategy-selection" icon={Bot} title="Strategy Selection" detail="Adaptive strategy status" /><QuickLink to="/precision-execution" icon={Crosshair} title="Precision Execution" detail="ACR, FVG, structure and levels" /><QuickLink to="/mt5-integration" icon={Radio} title="MT5 Direct" detail="Terminal connectivity diagnostics" /></div></section>
      </div>
    </div>
  );
}

function Metric({ label, value, detail, tone = "text-slate-100" }: { label: string; value: string; detail: string; tone?: string }) { return <article className="rounded-xl border border-slate-800 bg-slate-900 p-4"><p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{label}</p><p className={`mt-2 font-mono text-xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-[11px] text-slate-500">{detail}</p></article>; }
function Value({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-slate-950/70 p-3"><p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 truncate font-mono text-sm font-semibold text-slate-200">{value}</p></div>; }
function Row({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-2"><dt className="text-slate-500">{label}</dt><dd className="max-w-[65%] truncate text-right font-mono text-slate-200">{value}</dd></div>; }
function StatusCard({ icon: Icon, title, value, detail }: { icon: typeof Activity; title: string; value: string; detail: string }) { return <article className="rounded-xl border border-slate-800 bg-slate-900 p-4"><div className="flex items-center gap-2 text-xs font-semibold text-slate-300"><Icon className="h-4 w-4 text-cyan-300" />{title}</div><p className="mt-4 font-mono text-lg font-semibold text-slate-100">{value}</p><p className="mt-1 text-xs leading-relaxed text-slate-500">{detail}</p></article>; }
function QuickLink({ to, icon: Icon, title, detail }: { to: string; icon: typeof Activity; title: string; detail: string }) { return <Link to={to} className="group rounded-xl border border-slate-800 bg-slate-900 p-4 transition hover:border-cyan-400/50 hover:bg-slate-800"><div className="flex items-center justify-between"><Icon className="h-5 w-5 text-cyan-300" /><ArrowRight className="h-4 w-4 text-slate-600 transition group-hover:translate-x-1 group-hover:text-cyan-300" /></div><p className="mt-4 font-semibold">{title}</p><p className="mt-1 text-xs text-slate-500">{detail}</p></Link>; }
function formatNumber(value: number | null | undefined): string { return value == null || !Number.isFinite(value) ? "--" : value.toFixed(2); }
