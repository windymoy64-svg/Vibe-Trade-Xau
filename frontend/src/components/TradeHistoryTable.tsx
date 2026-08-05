import React, { useState } from "react";
import { Users, Bot, Search, Download, ChevronDown, ChevronUp } from "lucide-react";

type SourceType = "MANUAL" | "AUTO_BY_AI";
type TradeStatus = "closed" | "open" | "pending";

interface TradeRecord {
  id: string;
  timestamp: string;
  symbol: string;
  side: "BUY" | "SELL";
  volume: number;
  entryPrice: number;
  exitPrice?: number;
  pnl?: number;
  source: SourceType;
  status: TradeStatus;
  slippage?: number;
  commission?: number;
}

const mockTrades: TradeRecord[] = [
  { id: "TR-001", timestamp: "2026-08-04T14:50:00Z", symbol: "XAUUSD", side: "BUY", volume: 0.1, entryPrice: 2348.50, exitPrice: 2352.00, pnl: 35.00, source: "AUTO_BY_AI", status: "closed" },
  { id: "TR-002", timestamp: "2026-08-04T14:45:00Z", symbol: "XAUUSD", side: "SELL", volume: 0.15, entryPrice: 2350.00, exitPrice: 2347.50, pnl: 37.50, source: "AUTO_BY_AI", status: "closed" },
  { id: "TR-003", timestamp: "2026-08-04T14:40:00Z", symbol: "XAUUSD", side: "BUY", volume: 0.2, entryPrice: 2345.00, exitPrice: 2343.00, pnl: -40.00, source: "MANUAL", status: "closed" },
  { id: "TR-004", timestamp: "2026-08-04T14:35:00Z", symbol: "XAUUSD", side: "SELL", volume: 0.1, entryPrice: 2352.00, exitPrice: 2355.50, pnl: -35.00, source: "AUTO_BY_AI", status: "closed" },
  { id: "TR-005", timestamp: "2026-08-04T14:30:00Z", symbol: "XAUUSD", side: "BUY", volume: 0.25, entryPrice: 2347.00, exitPrice: 2350.00, pnl: 75.00, source: "MANUAL", status: "closed" },
  { id: "TR-006", timestamp: "2026-08-04T14:25:00Z", symbol: "XAUUSD", side: "SELL", volume: 0.1, entryPrice: 2354.00, exitPrice: 2351.00, pnl: 30.00, source: "AUTO_BY_AI", status: "closed" },
  { id: "TR-007", timestamp: "2026-08-04T14:20:00Z", symbol: "XAUUSD", side: "BUY", volume: 0.15, entryPrice: 2349.00, exitPrice: 2346.00, pnl: -45.00, source: "MANUAL", status: "closed" },
  { id: "TR-008", timestamp: "2026-08-04T14:15:00Z", symbol: "XAUUSD", side: "SELL", volume: 0.1, entryPrice: 2356.00, exitPrice: 2353.00, pnl: 30.00, source: "AUTO_BY_AI", status: "closed" },
  { id: "TR-009", timestamp: "2026-08-04T14:10:00Z", symbol: "XAUUSD", side: "BUY", volume: 0.2, entryPrice: 2350.00, exitPrice: 2354.00, pnl: 80.00, source: "AUTO_BY_AI", status: "closed" },
  { id: "TR-010", timestamp: "2026-08-04T14:05:00Z", symbol: "XAUUSD", side: "SELL", volume: 0.3, entryPrice: 2358.00, exitPrice: 2355.00, pnl: 90.00, source: "MANUAL", status: "closed" },
  { id: "TR-011", timestamp: "2026-08-04T14:00:00Z", symbol: "XAUUSD", side: "BUY", volume: 0.1, entryPrice: 2352.00, exitPrice: 2349.00, pnl: -30.00, source: "AUTO_BY_AI", status: "closed" },
  { id: "TR-012", timestamp: "2026-08-04T13:55:00Z", symbol: "XAUUSD", side: "SELL", volume: 0.2, entryPrice: 2355.00, exitPrice: 2352.00, pnl: 60.00, source: "MANUAL", status: "closed" },
];

export function TradeHistoryTable() {
  const [filterSource, setFilterSource] = useState<SourceType | "ALL">("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [sortField, setSortField] = useState<keyof TradeRecord>("timestamp");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const filteredTrades = mockTrades.filter((trade) => {
    const matchesSource = filterSource === "ALL" || trade.source === filterSource;
    const matchesSearch = searchTerm === "" || 
      trade.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      trade.id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSource && matchesSearch;
  });

  const sortedTrades = [...filteredTrades].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    if (typeof aVal === "string" && typeof bVal === "string") {
      return sortDirection === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }
    if (typeof aVal === "number" && typeof bVal === "number") {
      return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
    }
    return 0;
  });

  const handleSort = (field: keyof TradeRecord) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const toggleExpand = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const SourceIcon = ({ source }: { source: SourceType }) => {
    if (source === "AUTO_BY_AI") {
      return <Bot className="h-3.5 w-3.5 text-emerald-500" />;
    }
    return <Users className="h-3.5 w-3.5 text-sky-500" />;
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <svg className="h-5 w-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" /></svg>
            Trade History
          </h3>
          <p className="text-xs text-muted-foreground">Complete record of all executions with source attribution</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className="inline-flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted">
            <Download className="h-3.5 w-3.5" /> Export CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-card p-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by symbol or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-md border bg-muted/50 pl-10 pr-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <select
          value={filterSource}
          onChange={(e) => setFilterSource(e.target.value as SourceType | "ALL")}
          className="rounded-md border bg-muted/50 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          <option value="ALL">All Sources</option>
          <option value="MANUAL">Manual Only</option>
          <option value="AUTO_BY_AI">AI Automated Only</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="px-4 py-3 font-medium">
                  <button onClick={() => handleSort("timestamp")} className="flex items-center gap-1 hover:text-primary">
                    Time {sortField === "timestamp" && (sortDirection === "asc" ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />)}
                  </button>
                </th>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Symbol</th>
                <th className="px-4 py-3 font-medium">Side</th>
                <th className="px-4 py-3 font-medium">Volume</th>
                <th className="px-4 py-3 font-medium">
                  <button onClick={() => handleSort("entryPrice")} className="flex items-center gap-1 hover:text-primary">
                    Entry {sortField === "entryPrice" && (sortDirection === "asc" ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />)}
                  </button>
                </th>
                <th className="px-4 py-3 font-medium">Exit</th>
                <th className="px-4 py-3 font-medium">
                  <button onClick={() => handleSort("pnl")} className="flex items-center gap-1 hover:text-primary">
                    P/L {sortField === "pnl" && (sortDirection === "asc" ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />)}
                  </button>
                </th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedTrades.map((trade) => (
                <React.Fragment key={trade.id}>
                  <tr className={`border-b transition-colors ${expandedRows.has(trade.id) ? "bg-primary/5" : "hover:bg-muted/30"}`}>
                    <td className="px-4 py-3 text-muted-foreground">{new Date(trade.timestamp).toLocaleString()}</td>
                    <td className="px-4 py-3 font-mono font-semibold">{trade.id}</td>
                    <td className="px-4 py-3 font-semibold">{trade.symbol}</td>
                    <td className={`px-4 py-3 font-bold ${trade.side === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>{trade.side}</td>
                    <td className="px-4 py-3 font-mono">{trade.volume.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono">${trade.entryPrice.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono">{trade.exitPrice ? `$${trade.exitPrice.toFixed(2)}` : "-"}</td>
                    <td className={`px-4 py-3 font-mono font-semibold ${trade.pnl !== undefined && trade.pnl >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                      {trade.pnl !== undefined ? `${trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)} USD` : "-"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        trade.source === "AUTO_BY_AI" ? "bg-emerald-500/10 text-emerald-500" : "bg-sky-500/10 text-sky-500"
                      }`}>
                        <SourceIcon source={trade.source} />
                        {trade.source === "AUTO_BY_AI" ? "AI" : "Manual"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        trade.status === "closed" ? "bg-slate-500/10 text-slate-500" :
                        trade.status === "open" ? "bg-amber-500/10 text-amber-500" : "bg-primary/10 text-primary"
                      }`}>
                        {trade.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => toggleExpand(trade.id)}
                        className="inline-flex items-center justify-center rounded p-1 hover:bg-muted"
                      >
                        {expandedRows.has(trade.id) ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                    </td>
                  </tr>
                  {expandedRows.has(trade.id) && (
                    <tr>
                      <td colSpan={11} className="bg-muted/20 px-4 py-4">
                        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                          <Detail label="Slippage" value={trade.slippage ? `${trade.slippage.toFixed(2)} pips` : "N/A"} />
                          <Detail label="Commission" value={trade.commission ? `$${trade.commission.toFixed(2)}` : "Included"} />
                          <Detail label="Hold Time" value="2h 15m" />
                          <Detail label="Market Regime" value="Ranging" />
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-3 sm:grid-cols-3">
        <SummaryCard label="Total Trades" value={String(mockTrades.length)} />
        <SummaryCard label="Manual Trades" value={String(mockTrades.filter(t => t.source === "MANUAL").length)} tone="text-sky-500" />
        <SummaryCard label="AI Trades" value={String(mockTrades.filter(t => t.source === "AUTO_BY_AI").length)} tone="text-emerald-500" />
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase text-muted-foreground">{label}</p>
      <p className="font-mono font-semibold text-sm">{value}</p>
    </div>
  );
}

function SummaryCard({ label, value, tone = "" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={`mt-1 font-mono text-xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
