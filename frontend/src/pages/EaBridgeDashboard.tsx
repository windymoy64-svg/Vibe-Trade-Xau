import { useState } from "react";
import { Bot, ChevronDown, ChevronUp, List, Radio, RefreshCw, Zap } from "lucide-react";
import { Link } from "react-router";
import { eaBridgePreview, type EaLogRecord, type EaLogLevel, type EaCommandRecord } from "@/data/ea-bridge";
import { EaConnectionDashboard, EaEngineStatus, EaFailSafeBanner } from "@/components/ea-bridge/ConnectionDashboard";
import { OrderControlPanel } from "@/components/ea-bridge/OrderControlPanel";
import { LiveXauusdPrice } from "@/components/ea-bridge/LiveXauusdPrice";
import { LivePositions } from "@/components/ea-bridge/LivePositions";
import { LivePendingOrders } from "@/components/ea-bridge/LivePendingOrders";
import { EaTerminalStatusIndicator } from "@/components/ea-bridge/EaTerminalStatusIndicator";

const commandTone: Record<EaCommandRecord["status"], string> = {
  SENT: "bg-sky-500/10 text-sky-500",
  ACKED: "bg-amber-500/10 text-amber-500",
  EXECUTED: "bg-emerald-500/10 text-emerald-500",
  REJECTED: "bg-rose-500/10 text-rose-500",
};

const logTone: Record<EaLogRecord["level"], string> = {
  INFO: "text-muted-foreground",
  WARNING: "text-amber-500",
  ERROR: "text-rose-500",
};

export function EaBridgeDashboard() {
  const [logs, setLogs] = useState(eaBridgePreview.logs);
  const [logsExpanded, setLogsExpanded] = useState(false);

  const onRefresh = () => {
    const at = new Date().toISOString();
    setLogs((current) => [
      { id: `session-${Date.now()}`, level: "INFO" as EaLogLevel, source: "engine", message: `Manual sync requested at ${at} — preview in page memory only.`, timestamp: at },
      ...current,
    ].slice(0, 50));
  };

  const metrics = eaBridgePreview.metrics;
  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
      <div>
        <Link to="/precision-execution" className="mb-4 inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"><Radio className="h-3.5 w-3.5" /> Precision Execution</Link>
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><Zap className="h-4 w-4" /> EA MQL5 bridge <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] tracking-normal text-amber-500">Preview only</span></div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">EA bridge dashboard</h1>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">Monitor connected MT5 terminals, verify synchronized execution, and review the fail-safe protection state.</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Link to="/ea-bridge/audit" className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"><List className="h-3.5 w-3.5" /> Audit trail</Link>
        <Link to="/ea-bridge/reconciliation" className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"><RefreshCw className="h-3.5 w-3.5" /> Reconciliation</Link>
        <Link to="/ea-bridge/trades/ea-trade-1840" className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"><Bot className="h-3.5 w-3.5" /> Trade diagnostic</Link>
        <button type="button" onClick={onRefresh} className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"><RefreshCw className="h-3.5 w-3.5" /> Refresh sync</button>
        <span className="rounded-full border px-3 py-1 text-xs text-muted-foreground">24 pipes live</span>
      </div>
    </header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Online terminals" value={String(metrics.online)} detail={`${metrics.total} EA registered`} tone="text-emerald-500" />
      <Metric label="Sync events" value={String(metrics.syncEvents)} detail="2h rolling window" />
      <Metric label="Pending orders" value={String(metrics.pendingOrders)} detail="Waiting in local MT5" tone="text-amber-500" />
      <Metric label="Open lots" value={metrics.openLots.toFixed(2)} detail="XAUUSD positions" />
    </section>

    <LiveXauusdPrice initial={eaBridgePreview.market} />
    <EaTerminalStatusIndicator connections={eaBridgePreview.connections} lastSyncAt={eaBridgePreview.engine.lastSyncAt} />

    <section className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
      <div className="space-y-5">
        <EaEngineStatus symbol="XAUUSD" timeframe={eaBridgePreview.engine.timeframe} tokenId={eaBridgePreview.engine.tokenId} status={eaBridgePreview.engine.status} lastSyncAt={eaBridgePreview.engine.lastSyncAt} />
        <EaConnectionDashboard connections={eaBridgePreview.connections} />
        <LivePendingOrders initial={eaBridgePreview.pendingOrders} onAction={(message) => setLogs((current) => [{ id: `session-${Date.now()}`, level: "INFO" as EaLogLevel, source: "pending-orders", message, timestamp: new Date().toISOString() }, ...current].slice(0, 50))} />
        <article className="rounded-xl border bg-card shadow-sm" aria-label="Synchronized execution audit">
          <PanelHeader icon={List} title="Command audit trail" detail="Timestamped actions sent from the engine and acknowledged by MT5." />
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead><tr className="border-b text-muted-foreground"><th className="px-5 py-2.5 font-medium">Action</th><th className="px-3 py-2.5 font-medium">Type</th><th className="px-3 py-2.5 font-medium">Volume</th><th className="px-3 py-2.5 font-medium">Price</th><th className="px-3 py-2.5 font-medium">Status</th><th className="px-5 py-2.5 text-right font-medium">Latency</th></tr></thead>
              <tbody>{eaBridgePreview.commands.map((command) => <tr key={command.id} className="border-b last:border-0"><td className="px-5 py-3">{command.action}</td><td className="px-3 py-3 font-mono">{command.type}</td><td className="px-3 py-3 font-mono">{command.volume.toFixed(3)}</td><td className="px-3 py-3 font-mono">{command.price.toFixed(2)}</td><td className="px-3 py-3"><span className={`rounded-full px-2 py-0.5 font-semibold ${commandTone[command.status]}`}>{command.status}</span></td><td className="px-5 py-3 text-right font-mono text-muted-foreground">{command.latencyMs}ms</td></tr>)}</tbody>
            </table>
          </div>
        </article>
      </div>

      <div className="space-y-5">
        <EaFailSafeBanner state={eaBridgePreview.failSafe.state} timeoutSeconds={eaBridgePreview.failSafe.timeoutSeconds} incidents={eaBridgePreview.failSafe.incidents} />
        <OrderControlPanel execution={eaBridgePreview.executions[0] ?? null} onAction={(message) => setLogs((current) => [{ id: `session-${Date.now()}`, level: "INFO" as EaLogLevel, source: "order-control", message, timestamp: new Date().toISOString() }, ...current].slice(0, 50))} />
        <LivePositions initial={eaBridgePreview.executions} />
        <article className="rounded-xl border bg-card shadow-sm" aria-label="EA activity log">
          <button type="button" onClick={() => setLogsExpanded((value) => !value)} className="flex w-full items-center justify-between gap-3 p-5 text-start" aria-expanded={logsExpanded}>
            <span>Engine activity log</span>
            <span className="text-xs text-muted-foreground">{logs.length} events</span>
            {logsExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
          </button>
          {logsExpanded && <ol className="space-y-2 border-t p-5"><li className="rounded-lg border px-3 py-2 text-xs text-muted-foreground">EA Terminal A · M5 feed streamed every {eaBridgePreview.engine.intervalMs}ms.</li>{logs.map((log) => <li key={log.id} className="flex flex-col gap-1 rounded-lg border px-3 py-2 sm:flex-row sm:items-center sm:justify-between"><span className={`text-xs ${logTone[log.level]}`}>{log.message}</span><span className="text-[10px] text-muted-foreground">{new Date(log.timestamp).toLocaleTimeString()}</span></li>)}</ol>}
        </article>
      </div>
    </section>
  </div>;
}

function PanelHeader({ icon: Icon, title, detail }: { icon: typeof Bot; title: string; detail: string }) { return <div className="flex items-start gap-3 border-b p-5"><span className="rounded-lg bg-primary/10 p-2 text-primary"><Icon className="h-4 w-4" /></span><div><h2 className="font-semibold">{title}</h2><p className="mt-0.5 text-xs text-muted-foreground">{detail}</p></div></div>; }
function Metric({ label, value, detail = "", tone = "text-foreground" }: { label: string; value: string; detail?: string; tone?: string }) { return <div className="rounded-xl border bg-card p-4"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div>; }
