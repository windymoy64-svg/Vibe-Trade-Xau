import { Cable, CheckCircle2, CircleOff, Radio, Server, Terminal } from "lucide-react";
import type { Mt5DirectPreviewData, Mt5PipelineStatus } from "@/data/mt5-direct";

const statusTone: Record<Mt5PipelineStatus, string> = {
  HEALTHY: "border-emerald-500/30 bg-emerald-500/5 text-emerald-500",
  DEGRADED: "border-amber-500/30 bg-amber-500/5 text-amber-500",
  OFFLINE: "border-rose-500/30 bg-rose-500/5 text-rose-500",
};

export function Mt5ConnectionIndicator({ terminal }: { terminal: Mt5DirectPreviewData["terminal"] }) {
  const StatusIcon = terminal.status === "OFFLINE" ? CircleOff : CheckCircle2;
  return (
    <section aria-label="MT5 connection indicator" className={`rounded-xl border p-5 ${statusTone[terminal.status]}`}>
      <div className="flex flex-col justify-between gap-4 xl:flex-row xl:items-center">
        <div className="flex items-start gap-3"><StatusIcon className="mt-0.5 h-5 w-5 shrink-0" /><div><div className="flex flex-wrap items-center gap-2"><h2 className="text-sm font-semibold text-foreground">MetaTrader 5 connection</h2><span className="rounded-full bg-background/80 px-2 py-0.5 text-[9px] font-semibold">{terminal.status}</span></div><p className="mt-1 text-xs text-muted-foreground">{terminal.broker} · account {terminal.account} · {terminal.latencyMs}ms</p><p className="mt-1 font-mono text-[10px] text-muted-foreground">Last heartbeat {new Date(terminal.lastHeartbeatAt).toLocaleString()}</p></div></div>
        <div className="flex flex-wrap items-center gap-2 text-[10px]"><Node icon={Server} label="Web engine" /><Connector /><Node icon={Cable} label="Python library" /><Connector /><Node icon={Terminal} label={`MT5 build ${terminal.build}`} /><Connector /><Node icon={Radio} label={terminal.server} /></div>
      </div>
    </section>
  );
}

function Node({ icon: Icon, label }: { icon: typeof Server; label: string }) { return <span className="inline-flex items-center gap-1.5 rounded-full border border-current/20 bg-background/80 px-2.5 py-1"><Icon className="h-3 w-3" /> {label}</span>; }
function Connector() { return <span aria-hidden="true" className="h-px w-4 bg-current/30" />; }
