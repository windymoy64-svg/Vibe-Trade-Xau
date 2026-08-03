import { Activity, ShieldAlert, ShieldCheck, Wifi } from "lucide-react";
import type { EaConnectionRecord, EaConnectionStatus } from "@/data/ea-bridge";
import { cn } from "@/lib/utils";

const statusTone: Record<EaConnectionStatus, { badge: string; dot: string; label: string }> = {
  ONLINE: { badge: "bg-emerald-500/10 text-emerald-500", dot: "bg-emerald-500", label: "Online" },
  OFFLINE: { badge: "bg-rose-500/10 text-rose-500", dot: "bg-rose-500", label: "Offline" },
  SYNCING: { badge: "bg-amber-500/10 text-amber-500", dot: "bg-amber-500", label: "Syncing" },
};

export function EaConnectionDashboard({ connections }: { connections: EaConnectionRecord[] }) {
  const connected = connections.filter((connection) => connection.status !== "OFFLINE").length;
  return (
    <section aria-label="EA connection dashboard" className="rounded-xl border bg-card shadow-sm">
      <header className="flex flex-col justify-between gap-3 border-b p-5 sm:flex-row sm:items-center">
        <div className="flex items-start gap-3">
          <span className="rounded-lg bg-primary/10 p-2 text-primary"><Wifi className="h-4 w-4" /></span>
          <div>
            <h2 className="font-semibold">EA connection dashboard</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">Real-time online/offline status for every MT5 terminal bridge.</p>
          </div>
        </div>
        <span className="text-xs text-muted-foreground">{`${connected} of ${connections.length} connected`}</span>
      </header>
      <ul className="divide-y">
        {connections.map((connection) => {
          const tone = statusTone[connection.status];
          return (
            <li key={connection.id} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center">
              <div className="flex flex-1 items-center gap-3">
                <span className={cn("h-2.5 w-2.5 shrink-0 rounded-full", tone.dot)} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{connection.label}</p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">{connection.broker} · {connection.account} · XAUUSD</p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {connection.latencyMs != null && <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-1 text-muted-foreground"><Activity className="h-3 w-3" /> {connection.latencyMs}ms</span>}
                <span className="rounded-full bg-background px-2 py-1 font-mono text-[10px] text-muted-foreground">{connection.platform}</span>
                <span className={cn("rounded-full px-2.5 py-1 font-semibold", tone.badge)}>{tone.label}</span>
              </div>
              {connection.errors.length > 0 && <p role="alert" className="w-full text-xs text-rose-500">{connection.errors[0]}</p>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function EaEngineStatus({ symbol, timeframe, tokenId, status, lastSyncAt }: {
  symbol: string; timeframe: string; tokenId: string; status: EaConnectionStatus; lastSyncAt: string;
}) {
  const tone = statusTone[status];
  return (
    <article aria-label="EA bridge engine status" className="rounded-xl border bg-card shadow-sm">
      <header className="flex items-start gap-3 border-b p-5">
        <span className="rounded-lg bg-emerald-500/10 p-2 text-emerald-500"><ShieldCheck className="h-4 w-4" /></span>
        <div>
          <h2 className="font-semibold">Precision engine bridge</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">Two-way MT5 bridge feeding real-time OHLC and executing routed orders.</p>
        </div>
      </header>
      <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Token" value={tokenId} />
        <Metric label="Status" value={status} tone={tone.badge} />
        <Metric label="Symbol / TF" value={`${symbol} · ${timeframe}`} />
        <Metric label="Last sync" value={new Date(lastSyncAt).toLocaleString()} />
      </div>
    </article>
  );
}

export function EaFailSafeBanner({ state, timeoutSeconds, incidents }: {
  state: "ACTIVE" | "NORMAL" | "RECOVERED"; timeoutSeconds: number; incidents: number;
}) {
  const active = state === "ACTIVE";
  const recovered = state === "RECOVERED";
  return (
    <section aria-label="EA fail-safe protection" className={cn("rounded-xl border p-5", active ? "border-rose-500/30 bg-rose-500/5" : recovered ? "border-amber-500/30 bg-amber-500/5" : "border-emerald-500/30 bg-emerald-500/5")}>
      <div className="flex gap-3">
        {active ? <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" /> : <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" />}
        <div>
          <h2 className="text-sm font-semibold">{active ? "Fail-safe active" : recovered ? "Fail-safe recovered" : "Fail-safe nominal"}</h2>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {active
              ? `Connection timeout exceeded ${timeoutSeconds}s. Emergency SL/TP applied to every open position and pending orders cancelled.`
              : recovered
                ? "Re-connection completed. Pending orders restored and open positions re-synchronized after the fail-safe."
                : "All EA connections healthy. Emergency parameters armed and standby."}
            {" "}{incidents} incident{incidents === 1 ? "" : "s"} recorded.
          </p>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value, tone = "text-foreground" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg bg-background/70 p-3">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={`mt-1 font-mono text-sm font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
