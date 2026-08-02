import { useEffect, useRef, useState } from "react";
import { Pause, Play, ScrollText } from "lucide-react";
import type { AutoTradeEngineStatus, AutoTradeLogEntry, AutoTradeLogLevel } from "@/data/auto-trade";

type LogFilter = "ALL" | AutoTradeLogLevel;

const previewMessages: Array<Pick<AutoTradeLogEntry, "level" | "message">> = [
  { level: "INFO", message: "Preview heartbeat confirmed strategy and risk configuration." },
  { level: "SIGNAL", message: "XAUUSD M15 candidate evaluated against the active evidence gates." },
  { level: "RISK", message: "Exposure check passed below the configured daily loss ceiling." },
];

export function AutoTradeExecutionLog({ logs, engineStatus, onPreviewLog }: { logs: AutoTradeLogEntry[]; engineStatus: AutoTradeEngineStatus; onPreviewLog: (level: AutoTradeLogLevel, message: string) => void }) {
  const [filter, setFilter] = useState<LogFilter>("ALL");
  const [streamEnabled, setStreamEnabled] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);
  const messageIndexRef = useRef(0);
  const filteredLogs = filter === "ALL" ? logs : logs.filter((entry) => entry.level === filter);

  useEffect(() => {
    if (!streamEnabled || engineStatus !== "RUNNING") return;
    const timer = window.setInterval(() => {
      const event = previewMessages[messageIndexRef.current % previewMessages.length];
      messageIndexRef.current += 1;
      onPreviewLog(event.level, event.message);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [engineStatus, onPreviewLog, streamEnabled]);

  useEffect(() => {
    if (streamEnabled) listRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [filteredLogs.length, streamEnabled]);

  return <article className="rounded-xl border bg-card shadow-sm">
    <div className="flex flex-col justify-between gap-3 border-b p-5 sm:flex-row sm:items-start">
      <div className="flex items-start gap-3"><span className="rounded-lg bg-primary/10 p-2 text-primary"><ScrollText className="h-4 w-4" /></span><div><h2 className="font-semibold">Real-time execution log</h2><p className="mt-0.5 text-xs text-muted-foreground">Scrollable preview decisions and risk events.</p></div></div>
      <button type="button" onClick={() => setStreamEnabled((current) => !current)} className="inline-flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[10px] font-medium hover:bg-muted">{streamEnabled ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}{streamEnabled ? "Pause stream" : "Resume stream"}</button>
    </div>
    <div className="flex flex-wrap items-center gap-2 border-b px-5 py-3"><span className={`mr-1 h-2 w-2 rounded-full ${streamEnabled && engineStatus === "RUNNING" ? "animate-pulse bg-emerald-500" : "bg-muted-foreground/40"}`} /><span className="mr-auto text-[10px] text-muted-foreground">{streamEnabled && engineStatus === "RUNNING" ? "Live preview updates every 5s" : "Stream waiting"}</span>{(["ALL", "INFO", "SIGNAL", "RISK"] as LogFilter[]).map((value) => <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)} className={`rounded-full px-2.5 py-1 text-[9px] font-semibold ${filter === value ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:text-foreground"}`}>{value}</button>)}</div>
    <div ref={listRef} className="max-h-80 overflow-y-auto divide-y" aria-label="Execution log entries">{filteredLogs.length ? filteredLogs.map((entry) => <LogRow key={entry.id} entry={entry} />) : <p className="p-8 text-center text-sm text-muted-foreground">No {filter === "ALL" ? "activity" : filter.toLowerCase()} logs yet.</p>}</div>
    <div className="border-t px-5 py-2 text-right text-[9px] text-muted-foreground">Showing {filteredLogs.length} of {logs.length} events · capped at 50</div>
  </article>;
}

function LogRow({ entry }: { entry: AutoTradeLogEntry }) { const tone = entry.level === "RISK" ? "text-amber-500" : entry.level === "SIGNAL" ? "text-sky-500" : "text-muted-foreground"; return <div className="flex gap-3 p-4"><span className={`mt-0.5 w-12 text-[9px] font-semibold ${tone}`}>{entry.level}</span><div className="min-w-0 flex-1"><p className="text-xs leading-relaxed">{entry.message}</p><time className="mt-1 block text-[9px] text-muted-foreground">{new Date(entry.timestamp).toLocaleString()}</time></div></div>; }