import { useState, useEffect } from "react";
import { Play, Square, RefreshCw, AlertTriangle, Activity, Clock, Terminal } from "lucide-react";

type LogType = "info" | "warning" | "error" | "success";

interface LatencyLog {
  id: string;
  timestamp: string;
  type: LogType;
  message: string;
  latencyMs?: number;
}

export function EaLatencySimulation() {
  const [isSimulating, setIsSimulating] = useState(false);
  const [logs, setLogs] = useState<LatencyLog[]>([]);
  const [latencyData, setLatencyData] = useState<number[]>(Array(20).fill(50));
  const [avgLatency, setAvgLatency] = useState(50);
  const [minLatency, setMinLatency] = useState(20);
  const [maxLatency, setMaxLatency] = useState(100);

  const addLog = (type: LogType, message: string, latencyMs?: number) => {
    setLogs((prev) => [
      {
        id: `log-${Date.now()}-${Math.random()}`,
        timestamp: new Date().toISOString(),
        type,
        message,
        latencyMs,
      },
      ...prev.slice(0, 49),
    ]);
  };

  const simulateNetworkEvent = () => {
    const scenarios = [
      { type: "success" as LogType, message: "MCP handshake successful", baseLatency: 30 },
      { type: "info" as LogType, message: "Token validated via MCP server", baseLatency: 15 },
      { type: "info" as LogType, message: "Connection heartbeat received", baseLatency: 25 },
      { type: "warning" as LogType, message: "High latency detected - retrying", baseLatency: 150 },
      { type: "error" as LogType, message: "Connection timeout - endpoint unreachable", baseLatency: 500 },
      { type: "warning" as LogType, message: "SSL certificate expiring in 7 days", baseLatency: 10 },
      { type: "success" as LogType, message: "Trade execution acknowledged", baseLatency: 80 },
      { type: "info" as LogType, message: "New MQL5 terminal connected", baseLatency: 45 },
    ];

    const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
    const latency = Math.floor(scenario.baseLatency + (Math.random() * scenario.baseLatency * 0.5));

    setLatencyData((prev) => [...prev.slice(1), latency]);
    setAvgLatency((prev) => Math.round((prev * 19 + latency) / 20));
    setMinLatency((prev) => Math.min(prev, latency));
    setMaxLatency((prev) => Math.max(prev, latency));

    addLog(scenario.type, scenario.message, latency);
  };

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isSimulating) {
      interval = setInterval(simulateNetworkEvent, 2000);
    }
    return () => clearInterval(interval);
  }, [isSimulating]);

  const handleReset = () => {
    setIsSimulating(false);
    setLogs([]);
    setLatencyData(Array(20).fill(50));
    setAvgLatency(50);
    setMinLatency(20);
    setMaxLatency(100);
  };

  const getLogColor = (type: LogType) => {
    switch (type) {
      case "success":
        return "text-emerald-500 bg-emerald-500/10";
      case "info":
        return "text-sky-500 bg-sky-500/10";
      case "warning":
        return "text-amber-500 bg-amber-500/10";
      case "error":
        return "text-rose-500 bg-rose-500/10";
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
      <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary">
            <Activity className="h-4 w-4" />
            MCP Network Simulation
            <span className="rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] tracking-normal text-rose-500">Test Only</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Latency & Error Simulation</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Simulate network conditions and error scenarios to test system resilience during EA deployment.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setIsSimulating(!isSimulating)}
            className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${
              isSimulating
                ? "bg-rose-500 text-white hover:bg-rose-500/90"
                : "bg-emerald-500 text-white hover:bg-emerald-500/90"
            }`}
          >
            {isSimulating ? <Square className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            {isSimulating ? "Stop" : "Start Simulation"}
          </button>
          <button
            onClick={handleReset}
            className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Reset
          </button>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-3 xl:grid-cols-4">
        <Metric label="Current Avg Latency" value={`${avgLatency}ms`} tone="text-emerald-500" />
        <Metric label="Minimum Observed" value={`${minLatency}ms`}>
          <p className="mt-1 text-xs text-muted-foreground">Best response time</p>
        </Metric>
        <Metric label="Maximum Observed" value={`${maxLatency}ms`}>
          <p className="mt-1 text-xs text-muted-foreground">Peak delay recorded</p>
        </Metric>
        <Metric label="Total Events" value={String(logs.length)}>
          <p className="mt-1 text-xs text-muted-foreground">Simulated interactions</p>
        </Metric>
      </section>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(400px,0.4fr)]">
        <article className="space-y-5">
          <div className="rounded-xl border bg-card p-5 shadow-sm">
            <h3 className="font-semibold mb-3">Latency Visualization</h3>
            <div className="flex h-32 items-end gap-1">
              {latencyData.map((value, index) => (
                <div
                  key={index}
                  className={`flex-1 rounded-t ${
                    value < 50
                      ? "bg-emerald-500"
                      : value < 100
                      ? "bg-amber-500"
                      : "bg-rose-500"
                  }`}
                  style={{ height: `${(value / 200) * 100}%` }}
                  title={`${value}ms`}
                />
              ))}
            </div>
            <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
              <span>20s ago</span>
              <span>Now</span>
            </div>
          </div>

          <div className="rounded-xl border bg-card shadow-sm">
            <div className="flex items-center justify-between border-b p-5">
              <h2 className="font-semibold">Event Log</h2>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="divide-y max-h-[400px] overflow-y-auto">
              {logs.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-12 text-center">
                  <Terminal className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">No events yet - start simulation</p>
                </div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="flex items-start gap-3 p-4 hover:bg-muted/50">
                    <div className={`rounded-full p-1.5 ${getLogColor(log.type)}`}>
                      {log.type === "error" ? (
                        <AlertTriangle className="h-3.5 w-3.5" />
                      ) : log.type === "warning" ? (
                        <AlertTriangle className="h-3.5 w-3.5" />
                      ) : log.type === "success" ? (
                        <Activity className="h-3.5 w-3.5" />
                      ) : (
                        <Activity className="h-3.5 w-3.5" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">{log.message}</p>
                      <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                        <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                        {log.latencyMs !== undefined && (
                          <>
                            <span>•</span>
                            <span className={`font-mono ${log.latencyMs < 50 ? "text-emerald-500" : log.latencyMs < 100 ? "text-amber-500" : "text-rose-500"}`}>
                              {log.latencyMs}ms
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </article>

        <aside className="space-y-4">
          <div className="rounded-xl border bg-card p-5 shadow-sm">
            <h3 className="font-semibold mb-3">Simulation Controls</h3>
            <div className="space-y-2">
              <button
                onClick={() => {
                  setIsSimulating(true);
                  simulateNetworkEvent();
                }}
                disabled={isSimulating}
                className="w-full rounded-lg border bg-card px-3 py-2 text-left text-xs font-medium hover:bg-muted disabled:opacity-50"
              >
                Trigger MCP Handshake
              </button>
              <button
                onClick={() => {
                  addLog("warning", "Simulated connection spike", Math.floor(Math.random() * 200) + 100);
                }}
                disabled={isSimulating}
                className="w-full rounded-lg border bg-card px-3 py-2 text-left text-xs font-medium hover:bg-muted disabled:opacity-50"
              >
                Inject High Latency
              </button>
              <button
                onClick={() => {
                  addLog("error", "Simulated token expiration", 1000);
                }}
                disabled={isSimulating}
                className="w-full rounded-lg border bg-card px-3 py-2 text-left text-xs font-medium hover:bg-muted disabled:opacity-50"
              >
                Simulate Auth Fail
              </button>
              <button
                onClick={() => {
                  addLog("info", "Endpoint failover triggered", 250);
                }}
                disabled={isSimulating}
                className="w-full rounded-lg border bg-card px-3 py-2 text-left text-xs font-medium hover:bg-muted disabled:opacity-50"
              >
                Failover Test
              </button>
            </div>
          </div>

          <div className="rounded-xl border bg-amber-500/5 p-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5" />
              <div className="text-xs text-amber-700">
                <p className="font-medium">Safety Notice</p>
                <p className="mt-1">
                  This simulation runs in browser memory only. No actual connections are made.
                  Use this to verify UI behavior under various network conditions.
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border bg-card p-5 shadow-sm">
            <h4 className="font-semibold mb-2">Performance Tips</h4>
            <ul className="space-y-1 text-xs text-muted-foreground">
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3 w-3 text-emerald-500" />
                Keep latencies under 100ms for optimal UX
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3 w-3 text-emerald-500" />
                Implement exponential backoff for retries
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-3 w-3 text-emerald-500" />
                Cache tokens to reduce auth overhead
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}

function Metric({ label, value, children, tone = "" }: { label: string; value: string; children?: React.ReactNode; tone?: string }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>{value}</p>
      {children}
    </div>
  );
}

function CheckCircle({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
