import { useState } from "react";
import { CheckCircle2, XCircle, Clock, RefreshCw, Server, Zap, ShieldCheck } from "lucide-react";

type ConnectionStatus = "connected" | "disconnected" | "connecting" | "error" | "timeout";

interface EAConnection {
  id: string;
  name: string;
  terminalId: string;
  endpoint: string;
  status: ConnectionStatus;
  lastHeartbeat?: string;
  latencyMs?: number;
  uptimeSeconds?: number;
}

const mockConnections: EAConnection[] = [
  {
    id: "conn-1",
    name: "Production Terminal A",
    terminalId: "MT5-PROD-01",
    endpoint: "mt5-prod-01.vibetrade.com:8443",
    status: "connected",
    lastHeartbeat: new Date(Date.now() - 1000).toISOString(),
    latencyMs: 42,
    uptimeSeconds: 86400 * 3,
  },
  {
    id: "conn-2",
    name: "Test Terminal B",
    terminalId: "MT5-TEST-02",
    endpoint: "mt5-test-02.vibetrade.com:8443",
    status: "connecting",
    lastHeartbeat: undefined,
    latencyMs: undefined,
    uptimeSeconds: undefined,
  },
  {
    id: "conn-3",
    name: "Backup Terminal C",
    terminalId: "MT5-BACKUP-03",
    endpoint: "mt5-backup-03.vibetrade.com:8443",
    status: "error",
    lastHeartbeat: new Date(Date.now() - 300000).toISOString(),
    latencyMs: undefined,
    uptimeSeconds: 3600,
  },
];

export function EaConnectionStatus() {
  const [connections, setConnections] = useState<EAConnection[]>(mockConnections);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const formatUptime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setConnections((prev) =>
        prev.map((conn) => ({
          ...conn,
          lastHeartbeat: new Date().toISOString(),
          latencyMs: conn.status === "connected" ? Math.floor(Math.random() * 50) + 20 : undefined,
        }))
      );
      setIsRefreshing(false);
    }, 1500);
  };

  const getStatusIcon = (status: ConnectionStatus) => {
    switch (status) {
      case "connected":
        return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case "disconnected":
        return <XCircle className="h-4 w-4 text-slate-500" />;
      case "connecting":
        return <Clock className="h-4 w-4 text-amber-500 animate-pulse" />;
      case "error":
        return <XCircle className="h-4 w-4 text-rose-500" />;
      case "timeout":
        return <Clock className="h-4 w-4 text-amber-500" />;
    }
  };

  const getStatusColor = (status: ConnectionStatus) => {
    switch (status) {
      case "connected":
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
      case "disconnected":
        return "bg-slate-500/10 text-slate-500 border-slate-500/20";
      case "connecting":
        return "bg-amber-500/10 text-amber-500 border-amber-500/20";
      case "error":
        return "bg-rose-500/10 text-rose-500 border-rose-500/20";
      case "timeout":
        return "bg-orange-500/10 text-orange-500 border-orange-500/20";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <Server className="h-5 w-5 text-primary" />
            EA Connections
          </h3>
          <p className="text-xs text-muted-foreground">Live connection status to MT5 terminals</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center gap-1 rounded-md border bg-card px-2 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50"
        >
          <RefreshCw className={`h-3 w-3 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      <div className="space-y-2">
        {connections.map((conn) => (
          <div
            key={conn.id}
            className={`rounded-lg border p-4 transition-colors ${getStatusColor(conn.status)}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-full bg-current/10 p-2">{getStatusIcon(conn.status)}</div>
                <div>
                  <p className="font-medium text-sm">{conn.name}</p>
                  <div className="flex items-center gap-2 text-[10px] opacity-80">
                    <span className="font-mono">{conn.terminalId}</span>
                    <span>•</span>
                    <span className="font-mono truncate max-w-[150px]">{conn.endpoint}</span>
                  </div>
                </div>
              </div>

              <div className="text-right">
                {conn.status === "connected" && conn.latencyMs !== undefined && (
                  <>
                    <p className="text-xs font-mono">{conn.latencyMs}ms</p>
                    <p className="text-[10px] opacity-80">{formatUptime(conn.uptimeSeconds || 0)}</p>
                  </>
                )}
                {conn.status === "connected" && !conn.latencyMs && (
                  <p className="text-xs">Connected</p>
                )}
                {conn.status === "connecting" && (
                  <p className="text-xs">Connecting...</p>
                )}
                {conn.status === "error" && (
                  <p className="text-xs">Connection failed</p>
                )}
              </div>
            </div>

            {conn.lastHeartbeat && conn.status === "connected" && (
              <div className="mt-3 flex items-center gap-2 text-[10px] opacity-70">
                <Zap className="h-3 w-3" />
                <span>Last heartbeat: {new Date(conn.lastHeartbeat).toLocaleTimeString()}</span>
              </div>
            )}

            {conn.status === "error" && (
              <div className="mt-3 flex items-center gap-2 rounded-md bg-rose-500/10 p-2 text-[10px]">
                <ShieldCheck className="h-3 w-3 text-rose-500" />
                <span>Check token validity and network connectivity</span>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Overall Health</span>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            <span className="text-emerald-500 font-medium">1/3 Online</span>
          </div>
        </div>
        <div className="mt-2 space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
            <span className="text-muted-foreground">1 connected</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500"></span>
            <span className="text-muted-foreground">1 connecting</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-500"></span>
            <span className="text-muted-foreground">1 error</span>
          </div>
        </div>
      </div>
    </div>
  );
}
