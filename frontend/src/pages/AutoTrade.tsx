import { Activity, AlertTriangle, Bot, CirclePause, CirclePlay, Eye, EyeOff, KeyRound, OctagonX, Save, ShieldCheck, SlidersHorizontal, Zap } from "lucide-react";
import { useCallback, useState } from "react";
import { Link } from "react-router";
import { autoTradePreviewData, type AutoTradeConnectionStatus, type AutoTradeEngineStatus, type AutoTradeLogEntry } from "@/data/auto-trade";
import { AutoTradeExecutionLog } from "@/components/auto-trade/AutoTradeExecutionLog";
import { CurrentTradeExecution } from "@/components/auto-trade/CurrentTradeExecution";

const fieldClass = "w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";
const statusTone: Record<AutoTradeEngineStatus, string> = {
  RUNNING: "bg-emerald-500/10 text-emerald-500",
  PAUSED: "bg-amber-500/10 text-amber-500",
  STOPPED: "bg-rose-500/10 text-rose-500",
};

export function AutoTrade() {
  const [status, setStatus] = useState<AutoTradeEngineStatus>(autoTradePreviewData.engineStatus);
  const [paperMode, setPaperMode] = useState(autoTradePreviewData.paperMode);
  const [symbol, setSymbol] = useState(autoTradePreviewData.symbol);
  const [timeframe, setTimeframe] = useState(autoTradePreviewData.timeframe);
  const [strategy, setStrategy] = useState(autoTradePreviewData.strategy);
  const [risk, setRisk] = useState(autoTradePreviewData.riskPerTrade);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [keySaved, setKeySaved] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<AutoTradeConnectionStatus>(autoTradePreviewData.apiConnection.status);
  const [lastConnectionCheck, setLastConnectionCheck] = useState<string | null>(autoTradePreviewData.apiConnection.lastCheckedAt);
  const [logs, setLogs] = useState(autoTradePreviewData.logs);
  const [robotEnabled, setRobotEnabled] = useState(autoTradePreviewData.robotControls.enabled);
  const [lotSize, setLotSize] = useState(autoTradePreviewData.robotControls.lotSize);
  const [stopLossPips, setStopLossPips] = useState(autoTradePreviewData.robotControls.stopLossPips);
  const [takeProfitPips, setTakeProfitPips] = useState(autoTradePreviewData.robotControls.takeProfitPips);
  const [controlsSaved, setControlsSaved] = useState(false);

  const addLog = useCallback((level: AutoTradeLogEntry["level"], message: string) => {
    setLogs((current) => [{ id: `session-${Date.now()}-${current.length + 1}`, level, message, timestamp: new Date().toISOString() }, ...current].slice(0, 50));
  }, []);
  const changeStatus = (next: AutoTradeEngineStatus) => {
    setStatus(next);
    addLog(next === "STOPPED" ? "RISK" : "INFO", `Preview engine changed to ${next.toLowerCase()}. No broker order was sent.`);
  };
  const saveKey = () => {
    const normalizedKey = apiKey.trim();
    if (normalizedKey.length < 8) return;
    const checkedAt = new Date().toISOString();
    const failed = normalizedKey.toLowerCase().startsWith("invalid");
    setKeySaved(!failed);
    setConnectionStatus(failed ? "ERROR" : "CONNECTED");
    setLastConnectionCheck(checkedAt);
    addLog(failed ? "RISK" : "INFO", failed ? "Preview API connection check failed. No network request was sent." : "Preview API key connected in page memory only. No network request was sent.");
  };
  const disconnectKey = () => {
    setApiKey("");
    setKeySaved(false);
    setConnectionStatus("DISCONNECTED");
    setLastConnectionCheck(new Date().toISOString());
    addLog("INFO", "Preview API key disconnected from page memory.");
  };
  const limits = autoTradePreviewData.robotControls.limits;
  const controlsValid = lotSize >= limits.minLot && lotSize <= limits.maxLot
    && stopLossPips >= limits.minStopLossPips && stopLossPips <= limits.maxStopLossPips
    && takeProfitPips >= limits.minTakeProfitPips && takeProfitPips <= limits.maxTakeProfitPips;
  const updateRobotEnabled = () => {
    const next = !robotEnabled;
    setRobotEnabled(next);
    setControlsSaved(false);
    addLog(next ? "INFO" : "RISK", `Preview robot ${next ? "activated" : "deactivated"}. No broker connection was changed.`);
  };
  const applyRobotControls = () => {
    if (!controlsValid) return;
    setControlsSaved(true);
    addLog("RISK", `Preview controls applied: ${lotSize.toFixed(2)} lot, SL ${stopLossPips} pips, TP ${takeProfitPips} pips.`);
  };

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
      <div><div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><Bot className="h-4 w-4" /> Auto Trade <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] tracking-normal text-amber-500">Preview only</span></div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Execution control center</h1><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Stage evidence-aware XAUUSD controls, inspect risk gates, and review engine activity before connecting any live execution path.</p></div>
      <div className="flex flex-wrap items-center gap-2"><Link to="/auto-trade/strategy-selection" className="rounded-lg border bg-card px-3 py-2 text-xs font-medium hover:bg-muted">Strategy auto-selection</Link><span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusTone[status]}`}>{status}</span><span className="rounded-full border px-3 py-1 text-xs text-muted-foreground">{paperMode ? "PAPER" : "LIVE DISABLED"}</span></div>
    </header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="Signals today" value={String(autoTradePreviewData.metrics.signalsToday)} detail={`${autoTradePreviewData.metrics.acceptedSignals} passed all gates`} />
      <Metric label="Open positions" value={String(autoTradePreviewData.metrics.openPositions)} detail="No broker exposure" tone="text-emerald-500" />
      <Metric label="Session P/L" value={`+${autoTradePreviewData.metrics.sessionPnl.toFixed(2)}R`} detail="Preview calculations" />
      <Metric label="Daily loss limit" value={`${autoTradePreviewData.dailyLossLimit}%`} detail="Hard-stop simulation" tone="text-amber-500" />
    </section>

    <section className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)]">
      <div className="space-y-5">
        <CurrentTradeExecution execution={autoTradePreviewData.currentExecution} />
        <article className="rounded-xl border bg-card shadow-sm"><PanelHeader icon={Zap} title="Engine controls" detail="All actions update preview state only." /><div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3"><Field label="Symbol"><select value={symbol} onChange={(event) => setSymbol(event.target.value)} className={fieldClass}><option>XAUUSD</option><option>EURUSD</option><option>GBPUSD</option></select></Field><Field label="Timeframe"><select value={timeframe} onChange={(event) => setTimeframe(event.target.value)} className={fieldClass}><option>M5</option><option>M15</option><option>H1</option></select></Field><Field label="Strategy"><select value={strategy} onChange={(event) => setStrategy(event.target.value)} className={fieldClass}><option>Evidence trend guard</option><option>Regime breakout filter</option><option>Session bias control</option></select></Field><Field label="Risk per trade"><div className="relative"><input aria-label="Risk per trade" type="number" min={0.1} max={2} step={0.1} value={risk} onChange={(event) => setRisk(Number(event.target.value))} className={`${fieldClass} pr-8`} /><span className="absolute right-3 top-2.5 text-xs text-muted-foreground">%</span></div></Field><div className="sm:col-span-2"><label className="flex h-full items-center justify-between gap-4 rounded-lg border bg-background p-3"><div><span className="text-sm font-medium">Paper execution only</span><p className="mt-0.5 text-xs text-muted-foreground">Live routing remains disabled in this preview.</p></div><button type="button" role="switch" aria-checked={paperMode} aria-label="Paper execution only" onClick={() => setPaperMode((current) => !current)} className={`relative h-6 w-11 rounded-full ${paperMode ? "bg-primary" : "bg-muted"}`}><span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-transform ${paperMode ? "translate-x-1" : "-translate-x-4"}`} /></button></label></div></div><div className="flex flex-wrap gap-2 border-t p-5"><button type="button" onClick={() => changeStatus(status === "RUNNING" ? "PAUSED" : "RUNNING")} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">{status === "RUNNING" ? <CirclePause className="h-4 w-4" /> : <CirclePlay className="h-4 w-4" />}{status === "RUNNING" ? "Pause preview" : "Start preview"}</button><button type="button" onClick={() => changeStatus("STOPPED")} className="inline-flex items-center gap-2 rounded-lg border border-rose-500/30 px-4 py-2 text-sm font-medium text-rose-500 hover:bg-rose-500/10"><OctagonX className="h-4 w-4" /> Emergency stop</button></div></article>

        <AutoTradeExecutionLog logs={logs} engineStatus={status} onPreviewLog={addLog} />
      </div>

      <div className="space-y-5">
        <article className="rounded-xl border bg-card shadow-sm">
          <PanelHeader icon={SlidersHorizontal} title="Robot controls" detail="Activation and order protection preview." />
          <div className="space-y-4 p-5">
            <div className="flex items-center justify-between gap-4 rounded-lg border bg-muted/30 p-3">
              <div><p className="text-xs font-medium">Robot activation</p><p className="mt-0.5 text-[10px] text-muted-foreground">State applies to this page session only.</p></div>
              <button type="button" role="switch" aria-checked={robotEnabled} aria-label="Robot activation" onClick={updateRobotEnabled} className={`relative h-6 w-11 rounded-full transition ${robotEnabled ? "bg-emerald-500" : "bg-muted-foreground/30"}`}><span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition ${robotEnabled ? "left-6" : "left-1"}`} /></button>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
              <NumberControl id="robot-lot-size" label="Lot size" value={lotSize} min={limits.minLot} max={limits.maxLot} step={0.01} suffix="lot" onChange={(value) => { setLotSize(value); setControlsSaved(false); }} />
              <NumberControl id="robot-stop-loss" label="Stop loss" value={stopLossPips} min={limits.minStopLossPips} max={limits.maxStopLossPips} step={1} suffix="pips" onChange={(value) => { setStopLossPips(value); setControlsSaved(false); }} />
              <NumberControl id="robot-take-profit" label="Take profit" value={takeProfitPips} min={limits.minTakeProfitPips} max={limits.maxTakeProfitPips} step={1} suffix="pips" onChange={(value) => { setTakeProfitPips(value); setControlsSaved(false); }} />
            </div>
            {!controlsValid && <p role="alert" className="text-xs text-rose-500">Values must remain inside the displayed preview limits.</p>}
            <button type="button" disabled={!controlsValid} onClick={applyRobotControls} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"><Save className="h-3.5 w-3.5" /> Apply preview controls</button>
            {controlsSaved && <p className="flex items-center gap-2 text-xs text-emerald-500"><ShieldCheck className="h-4 w-4" /> Robot controls applied to page memory.</p>}
          </div>
        </article>
        <article className="rounded-xl border bg-card shadow-sm"><PanelHeader icon={KeyRound} title="Execution API key" detail="Mock credential gate for layout testing." /><div className="space-y-4 p-5"><ConnectionStatus status={connectionStatus} /><div className="grid grid-cols-2 gap-3 rounded-lg bg-muted/40 p-3 text-xs"><Meta label="Provider" value={autoTradePreviewData.apiConnection.provider} /><Meta label="Environment" value={autoTradePreviewData.apiConnection.environment} /></div><div><label htmlFor="auto-trade-api-key" className="text-xs font-medium">API key</label><div className="relative mt-1.5"><input id="auto-trade-api-key" type={showKey ? "text" : "password"} value={apiKey} onChange={(event) => { setApiKey(event.target.value); setKeySaved(false); setConnectionStatus("DISCONNECTED"); }} placeholder={autoTradePreviewData.apiKeyHint} autoComplete="off" spellCheck={false} className={`${fieldClass} pr-10`} /><button type="button" aria-label={showKey ? "Hide API key" : "Show API key"} onClick={() => setShowKey((current) => !current)} className="absolute right-3 top-2.5 text-muted-foreground">{showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></div>{apiKey.length > 0 && apiKey.length < 8 && <p role="alert" className="text-xs text-rose-500">Use at least 8 characters for the preview key.</p>}<div className="grid grid-cols-2 gap-2"><button type="button" disabled={apiKey.trim().length < 8} onClick={saveKey} className="rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50">Test connection</button><button type="button" disabled={connectionStatus === "DISCONNECTED" && !apiKey} onClick={disconnectKey} className="rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50">Disconnect</button></div>{keySaved && <p className="flex items-center gap-2 text-xs text-emerald-500"><ShieldCheck className="h-4 w-4" /> Preview connection verified for this page session.</p>}{connectionStatus === "ERROR" && <p role="alert" className="text-xs text-rose-500">Preview connection failed. Check the key format and try again.</p>}{lastConnectionCheck && <p className="text-[10px] text-muted-foreground">Last checked {new Date(lastConnectionCheck).toLocaleString()}</p>}<p className="text-[10px] leading-relaxed text-muted-foreground">The value is not sent to a backend and is not written to browser storage.</p></div></article>
        <article className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5"><div className="flex gap-3"><AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" /><div><h2 className="text-sm font-semibold">No live execution</h2><p className="mt-1 text-xs leading-relaxed text-muted-foreground">This screen uses typed preview data. Start, pause, emergency stop, and API key actions cannot place, cancel, or modify broker orders.</p></div></div></article>
      </div>
    </section>
  </div>;
}

function PanelHeader({ icon: Icon, title, detail }: { icon: typeof Activity; title: string; detail: string }) { return <div className="flex items-start gap-3 border-b p-5"><span className="rounded-lg bg-primary/10 p-2 text-primary"><Icon className="h-4 w-4" /></span><div><h2 className="font-semibold">{title}</h2><p className="mt-0.5 text-xs text-muted-foreground">{detail}</p></div></div>; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span>{children}</label>; }
function NumberControl({ id, label, value, min, max, step, suffix, onChange }: { id: string; label: string; value: number; min: number; max: number; step: number; suffix: string; onChange: (value: number) => void }) { return <div><label htmlFor={id} className="text-xs font-medium">{label}</label><div className="relative mt-1.5"><input id={id} type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(event.target.valueAsNumber)} className={`${fieldClass} pr-14 font-mono`} /><span className="pointer-events-none absolute right-3 top-2.5 text-[10px] text-muted-foreground">{suffix}</span></div><p className="mt-1 text-[9px] text-muted-foreground">Allowed {min}–{max} {suffix}</p></div>; }
function ConnectionStatus({ status }: { status: AutoTradeConnectionStatus }) { const tone = status === "CONNECTED" ? "bg-emerald-500/10 text-emerald-500" : status === "ERROR" ? "bg-rose-500/10 text-rose-500" : "bg-muted text-muted-foreground"; return <div className="flex items-center justify-between gap-3"><span className="text-xs font-medium">Connection status</span><span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${tone}`}>{status}</span></div>; }
function Meta({ label, value }: { label: string; value: string }) { return <div><p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-medium">{value}</p></div>; }
function Metric({ label, value, detail, tone = "text-foreground" }: { label: string; value: string; detail: string; tone?: string }) { return <article className="rounded-xl border bg-card p-5"><p className="text-xs text-muted-foreground">{label}</p><p className={`mt-2 text-2xl font-semibold ${tone}`}>{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></article>; }
