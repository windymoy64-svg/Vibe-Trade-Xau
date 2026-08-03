import { Activity, Cable, CircleCheck, CircleOff, Server } from "lucide-react";
import type { EaConnectionRecord } from "@/data/ea-bridge";

export function EaTerminalStatusIndicator({ connections, lastSyncAt }: { connections: EaConnectionRecord[]; lastSyncAt: string }) {
  const online = connections.filter((connection) => connection.status === "ONLINE");
  const syncing = connections.filter((connection) => connection.status === "SYNCING");
  const offline = connections.filter((connection) => connection.status === "OFFLINE");
  const healthy = offline.length === 0 && syncing.length === 0;
  const averageLatency = online.length === 0 ? null : Math.round(online.reduce((sum, connection) => sum + (connection.latencyMs ?? 0), 0) / online.length);

  return (
    <section aria-label="EA terminal connection status" className={`rounded-xl border p-4 ${healthy ? "border-emerald-500/30 bg-emerald-500/5" : "border-amber-500/30 bg-amber-500/5"}`}>
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
        <div className="flex items-center gap-3">
          {healthy ? <CircleCheck className="h-5 w-5 text-emerald-500" /> : <Activity className="h-5 w-5 text-amber-500" />}
          <div><div className="flex flex-wrap items-center gap-2"><h2 className="text-sm font-semibold">EA-terminal link</h2><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${healthy ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"}`}>{healthy ? "HEALTHY" : "DEGRADED"}</span></div><p className="mt-0.5 text-xs text-muted-foreground">Heartbeat {new Date(lastSyncAt).toLocaleTimeString()} · {averageLatency == null ? "No online latency" : `${averageLatency}ms average latency`}</p></div>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[10px]">
          <Node icon={Server} label="Precision engine" state="ONLINE" />
          <span className="h-px w-4 bg-border" />
          <Node icon={Cable} label="Local bridge" state="ONLINE" />
          <span className="h-px w-4 bg-border" />
          <Node icon={offline.length > 0 ? CircleOff : Activity} label={`${online.length} online · ${syncing.length} syncing · ${offline.length} offline`} state={offline.length > 0 ? "DEGRADED" : "ONLINE"} />
        </div>
      </div>
    </section>
  );
}

function Node({ icon: Icon, label, state }: { icon: typeof Server; label: string; state: "ONLINE" | "DEGRADED" }) {
  return <span className={`inline-flex items-center gap-1.5 rounded-full border bg-background px-2.5 py-1 ${state === "ONLINE" ? "text-emerald-500" : "text-amber-500"}`}><Icon className="h-3 w-3" /> {label}</span>;
}
