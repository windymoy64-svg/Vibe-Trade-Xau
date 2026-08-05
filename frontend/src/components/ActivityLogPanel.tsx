import { useState } from "react";
import { Activity, ToggleLeft, Shield, AlertTriangle, Clock, FileText } from "lucide-react";

type LogType = "mode_change" | "emergency_trigger" | "execution" | "warning";

interface ActivityLog {
  id: string;
  timestamp: string;
  type: LogType;
  category: "mode" | "emergency" | "execution" | "system";
  title: string;
  description: string;
  details?: Record<string, string>;
}

const mockLogs: ActivityLog[] = [
  {
    id: "LOG-001",
    timestamp: "2026-08-04T14:55:00Z",
    type: "mode_change",
    category: "mode",
    title: "Mode Switched to Manual",
    description: "Trading mode changed from AI automated to manual execution",
    details: { "From": "AUTO_BY_AI", "To": "MANUAL", "User": "Trader_001" },
  },
  {
    id: "LOG-002",
    timestamp: "2026-08-04T14:50:00Z",
    type: "emergency_trigger",
    category: "emergency",
    title: "Emergency Close Triggered - POS-003",
    description: "Position manually closed due to user request",
    details: { "Position": "POS-003", "Symbol": "XAUUSD", "Reason": "Market volatility", "P/L": "-150.00 USD" },
  },
  {
    id: "LOG-003",
    timestamp: "2026-08-04T14:45:00Z",
    type: "execution",
    category: "execution",
    title: "Trade Executed - AUTO_BY_AI",
    description: "AI-generated buy order executed on XAUUSD",
    details: { "Order": "TR-045", "Side": "BUY", "Volume": "0.1 lots", "Price": "2348.50" },
  },
  {
    id: "LOG-004",
    timestamp: "2026-08-04T14:40:00Z",
    type: "warning",
    category: "system",
    title: "High Latency Detected",
    description: "MCP connection latency exceeded threshold",
    details: { "Latency": "250ms", "Threshold": "100ms", "Endpoint": "mt5-prod-01" },
  },
  {
    id: "LOG-005",
    timestamp: "2026-08-04T14:35:00Z",
    type: "mode_change",
    category: "mode",
    title: "Mode Switched to Auto",
    description: "Trading mode changed from manual to AI automated execution",
    details: { "From": "MANUAL", "To": "AUTO_BY_AI", "User": "Trader_001" },
  },
  {
    id: "LOG-006",
    timestamp: "2026-08-04T14:30:00Z",
    type: "emergency_trigger",
    category: "emergency",
    title: "Auto Emergency Stop Activated",
    description: "System triggered emergency stop due to drawdown limit",
    details: { "Drawdown": "-5.2%", "Limit": "-5.0%", "Positions Closed": "3" },
  },
  {
    id: "LOG-007",
    timestamp: "2026-08-04T14:25:00Z",
    type: "execution",
    category: "execution",
    title: "Trade Executed - MANUAL",
    description: "Manual sell order placed by trader",
    details: { "Order": "TR-044", "Side": "SELL", "Volume": "0.2 lots", "Price": "2352.00" },
  },
];

export function ActivityLogPanel() {
  const [filterCategory, setFilterCategory] = useState<"ALL" | "mode" | "emergency" | "execution" | "system">("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  const filteredLogs = mockLogs.filter((log) => {
    const matchesCategory = filterCategory === "ALL" || log.category === filterCategory;
    const matchesSearch =
      searchTerm === "" ||
      log.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getIconForCategory = (category: string) => {
    if (category === "emergency") return <AlertTriangle className="h-5 w-5 text-rose-500" />;
    if (category === "mode") return <ToggleLeft className="h-5 w-5 text-sky-500" />;
    if (category === "execution") return <Activity className="h-5 w-5 text-emerald-500" />;
    return <FileText className="h-5 w-5 text-muted-foreground" />;
  };

  const getTypeBadge = (type: LogType) => {
    switch (type) {
      case "mode_change":
        return { label: "Mode Change", bg: "bg-sky-500/10", text: "text-sky-500" };
      case "emergency_trigger":
        return { label: "Emergency", bg: "bg-rose-500/10", text: "text-rose-500" };
      case "execution":
        return { label: "Execution", bg: "bg-emerald-500/10", text: "text-emerald-500" };
      case "warning":
        return { label: "Warning", bg: "bg-amber-500/10", text: "text-amber-500" };
    }
  };

  const getShortTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <Clock className="h-5 w-5 text-primary" />
            Activity Log
          </h3>
          <p className="text-xs text-muted-foreground">Track all mode changes and emergency triggers</p>
        </div>
        <div className="flex gap-2">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value as any)}
            className="rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted focus:border-primary focus:outline-none"
          >
            <option value="ALL">All Categories</option>
            <option value="mode">Mode Changes</option>
            <option value="emergency">Emergency Triggers</option>
            <option value="execution">Executions</option>
            <option value="system">System</option>
          </select>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <input
          type="text"
          placeholder="Search logs..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full rounded-lg border bg-card px-4 py-2.5 pr-10 text-sm focus:border-primary focus:outline-none"
        />
        <svg className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>

      {/* Log Entries */}
      <div className="space-y-2">
        {filteredLogs.map((log) => {
          const badge = getTypeBadge(log.type);
          return (
            <div key={log.id} className="group rounded-xl border bg-card p-4 transition-colors hover:bg-muted/50">
              <div className="flex items-start gap-3">
                <div className="mt-0.5">{getIconForCategory(log.category)}</div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold ${badge.bg} ${badge.text}`}>
                      {badge.label}
                    </span>
                    <span className="text-xs text-muted-foreground">{getShortTime(log.timestamp)}</span>
                    <span className="font-mono text-xs text-muted-foreground">{log.id}</span>
                  </div>
                  
                  <h4 className="mt-1 font-semibold">{log.title}</h4>
                  <p className="text-sm text-muted-foreground">{log.description}</p>

                  {/* Details */}
                  {log.details && Object.keys(log.details).length > 0 && (
                    <div className="mt-3 grid grid-cols-2 gap-2 rounded-lg bg-muted/50 p-3">
                      {Object.entries(log.details).map(([key, value]) => (
                        <div key={key}>
                          <p className="text-[10px] uppercase text-muted-foreground">{key}</p>
                          <p className="font-mono text-xs font-semibold">{value}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {filteredLogs.length === 0 && (
        <div className="rounded-xl border border-dashed p-12 text-center">
          <FileText className="mx-auto h-10 w-10 text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">No logs found</p>
          <p className="text-xs text-muted-foreground mt-1">Try adjusting your filters or search term</p>
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid gap-3 sm:grid-cols-4">
        <SummaryCard label="Total Events" value={String(mockLogs.length)} icon={<Clock className="h-4 w-4" />} />
        <SummaryCard label="Mode Changes" value={String(mockLogs.filter(l => l.category === "mode").length)} icon={<ToggleLeft className="h-4 w-4 text-sky-500" />} tone="text-sky-500" />
        <SummaryCard label="Emergency Actions" value={String(mockLogs.filter(l => l.category === "emergency").length)} icon={<Shield className="h-4 w-4 text-rose-500" />} tone="text-rose-500" />
        <SummaryCard label="Executions" value={String(mockLogs.filter(l => l.category === "execution").length)} icon={<Activity className="h-4 w-4 text-emerald-500" />} tone="text-emerald-500" />
      </div>

      {/* Info Banner */}
      <div className="rounded-xl border bg-amber-500/5 p-4">
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5" />
          <div className="text-xs text-amber-700">
            <p className="font-medium">Audit Trail Information</p>
            <ul className="mt-1 list-disc space-y-1 pl-4">
              <li>All mode switches are recorded for compliance review</li>
              <li>Emergency triggers require documented justification</li>
              <li>Logs are immutable and retained for 90 days</li>
              <li>Export available in CSV format for external audits</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, icon, tone = "" }: { label: string; value: string; icon?: React.ReactNode; tone?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
        {icon && <div>{icon}</div>}
      </div>
      <p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
