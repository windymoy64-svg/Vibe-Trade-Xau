import { Play, Settings, ShieldCheck, Square, Wifi, WifiOff, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TerminalChart } from "@/components/auto-trade/TerminalChart";
import { terminalApi, type AutoTradeConfig, type AutoTradeEntryAreaCandidate, type AutoTradeRunnerStatus, type ExecutionLog, type McpToken, type Mt5Bar, type Mt5ConfigurationInput, type Mt5LiveSnapshot, type Mt5Position } from "@/lib/trading-terminal-api";

// Helper: konversi timeframe (M1/M5/M15/H1/dll) ke detik.
// Format MT5 menaruh unit di DEPAN angka ("H1" = 1 jam), jadi pola harus
// dibaca sebagai <unit><angka>, bukan <angka><unit>.
const timeframeToSeconds = (tf: string): number => {
  const match = tf.trim().toUpperCase().match(/^([SMHDW])(\d+)$/);
  if (!match) return 0; // format tidak dikenal -> countdown "--:--"
  const unit = match[1];
  const value = parseInt(match[2], 10);
  if (!Number.isFinite(value) || value <= 0) return 0;
  switch (unit) {
    case "S": return value; // seconds
    case "M": return value * 60; // minutes
    case "H": return value * 3600; // hours
    case "D": return value * 86400; // days
    case "W": return value * 604800; // weeks
    default: return value * 60;
  }
};

// Helper: hitung detik tersisa ke penutupan candle berikutnya.
// Candle broker selalu tutup pada boundary epoch UTC (mis. M5 tutup tiap
// kelipatan 5 menit), sehingga countdown dihitung dari waktu sekarang.
const getNextCandleCountdown = (timeframe: string): string => {
  const timeframeSeconds = timeframeToSeconds(timeframe);
  if (timeframeSeconds <= 0) return "--:--";

  const now = Date.now() / 1000;
  const nextCloseTime = Math.ceil((now + 1e-6) / timeframeSeconds) * timeframeSeconds;
  const secondsRemaining = Math.max(0, Math.round(nextCloseTime - now));

  // Untuk timeframe besar (>= 1 jam) tampilkan HH:MM, selain itu MM:SS.
  if (timeframeSeconds >= 3600) {
    const hrs = Math.floor(secondsRemaining / 3600);
    const mins = Math.floor((secondsRemaining % 3600) / 60);
    return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}`;
  }
  const mins = Math.floor(secondsRemaining / 60);
  const secs = secondsRemaining % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
};

type BotStatus = "RUNNING" | "STOPPED";

export function AutoTrade() {
  const [snapshot, setSnapshot] = useState<Mt5LiveSnapshot | null>(null);
  const [config, setConfig] = useState<AutoTradeConfig | null>(null);
  const [symbol, setSymbol] = useState("XAUUSD");
  const [timeframe, setTimeframe] = useState("M30");
  const [lotSize, setLotSize] = useState(0.01);
  const [stopLoss, setStopLoss] = useState(30);
  const [takeProfit, setTakeProfit] = useState(60);
  const [risk, setRisk] = useState(0.5);
  const [dailyLoss, setDailyLoss] = useState(2);
  const [paperMode, setPaperMode] = useState(true);
  const [botStatus, setBotStatus] = useState<BotStatus>("STOPPED");
  const [logs, setLogs] = useState<ExecutionLog[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [notice, setNotice] = useState("Memeriksa koneksi MT5/MCPâ€¦");
  const [saving, setSaving] = useState(false);
  const [bars, setBars] = useState<Mt5Bar[]>([]);
  const [mcpToken, setMcpToken] = useState<McpToken | null>(null);
  const [runnerStatus, setRunnerStatus] = useState<AutoTradeRunnerStatus | null>(null);

  // Polling tiap 1 detik tidak boleh menimpa angka yang sedang diedit user.
  // `settingsOpenRef` dibaca di dalam `refresh` lewat ref supaya interval tidak
  // ikut restart, dan `configHydratedRef` memastikan config hanya dipakai untuk
  // hydrate form sekali (saat load pertama / setelah simpan).
  const settingsOpenRef = useRef(false);
  const configHydratedRef = useRef(false);
  useEffect(() => { settingsOpenRef.current = settingsOpen; }, [settingsOpen]);
  useEffect(() => {
    void terminalApi.activeMcpToken()
      .then(setMcpToken)
      .catch(() => setMcpToken(null));
  }, []);

  const applyConfig = useCallback((value: AutoTradeConfig) => {
    setConfig(value); setSymbol(value.symbol); setTimeframe(value.timeframe);
    setLotSize(value.robotControls.lotSize); setStopLoss(value.robotControls.stopLossPips);
    setTakeProfit(value.robotControls.takeProfitPips); setRisk(value.riskPerTrade);
    setDailyLoss(value.dailyLossLimit); setPaperMode(value.paperMode);
    configHydratedRef.current = true;
  }, []);
  const refresh = useCallback(async () => {
    const [marketResult, configResult, logResult, runnerResult] = await Promise.allSettled([terminalApi.liveSnapshot(symbol, timeframe), terminalApi.configurations(), terminalApi.logs(symbol), terminalApi.runnerStatus()]);
    if (marketResult.status === "fulfilled") {
      setSnapshot(marketResult.value);
      setBars(marketResult.value.bars.map((bar) => ({ timestamp: new Date(bar.time * 1000).toISOString(), open: bar.open, high: bar.high, low: bar.low, close: bar.close, volume: bar.real_volume || 0, tickVolume: bar.tick_volume || 0, spread: bar.spread || 0, symbol: marketResult.value.symbol, timeframe: marketResult.value.timeframe })));
    } else setSnapshot(null);
    if (configResult.status === "fulfilled" && configResult.value[0]) {
      // Selalu jaga `config` (dipakai START + PUT saat simpan), tapi jangan
      // pernah menimpa nilai input saat modal terbuka atau setelah hydrate awal.
      if (!configHydratedRef.current && !settingsOpenRef.current) applyConfig(configResult.value[0]);
      else setConfig(configResult.value[0]);
    }
    if (logResult.status === "fulfilled") setLogs(logResult.value);
    if (runnerResult.status === "fulfilled") { setRunnerStatus(runnerResult.value); setBotStatus(runnerResult.value.running ? "RUNNING" : "STOPPED"); }
    setNotice(marketResult.status === "fulfilled" ? "REALTIME Â· MT5 terminal feed aktif." : `OFFLINE Â· ${marketResult.reason instanceof Error ? marketResult.reason.message : "MT5 tidak tersedia"}`);
  }, [applyConfig, symbol, timeframe]);
  useEffect(() => { void refresh(); const timer = window.setInterval(refresh, 1_000); return () => window.clearInterval(timer); }, [refresh]);

  const latest = bars[bars.length - 1];
  // Countdown candle harus punya ticker sendiri: `refresh` hanya men-set state
  // saat datanya berubah, jadi tanpa ini angka NEXT CYCLE tidak pernah
  // ter-render ulang tiap detik.
  const [nextCycle, setNextCycle] = useState(() => getNextCandleCountdown(timeframe));
  useEffect(() => {
    const tick = () => setNextCycle(getNextCandleCountdown(timeframe));
    tick();
    const timer = window.setInterval(tick, 1_000);
    return () => window.clearInterval(timer);
  }, [timeframe]);
  const executed = logs.filter((log) => log.status === "EXECUTED" || log.status === "CLOSED");
  const openPositions = snapshot?.positions || [];
  const wins = executed.filter((log) => /profit|take profit|\btp\b/i.test(log.message)).length;
  const signal = useMemo(() => logs.find((log) => log.level === "SIGNAL"), [logs]);
  const startBot = async () => {
    // First, stop any existing runner to ensure clean state
    if (botStatus === "RUNNING") {
      try { await terminalApi.stopRunner(); } catch {}
      await new Promise(r => setTimeout(r, 500)); // Give backend time to stop
    }
    
    if (!snapshot?.connected) return setNotice("Start ditolak: MT5 terminal belum terhubung.");
    if (!config) { setNotice("Simpan Trading Rules terlebih dahulu."); return setSettingsOpen(true); }
    try { 
      const status = await terminalApi.startRunner({ symbol, timeframe, lotSize, stopLossPips: stopLoss, takeProfitPips: takeProfit, paperMode }); 
      setRunnerStatus(status); 
      setBotStatus("RUNNING"); 
      setNotice(status.message || "Auto trade started successfully."); 
    } catch (error) { 
      setBotStatus("STOPPED"); 
      setNotice(`Start ditolak: ${error instanceof Error ? error.message : "Unknown error"}`); 
    }
  };
  const stopBot = async () => { 
    try { 
      const status = await terminalApi.stopRunner(); 
      setRunnerStatus(status); 
      setBotStatus("STOPPED"); 
      setNotice(status.message || "Auto trade stopped."); 
    } catch (error) { 
      setBotStatus("STOPPED");
      setRunnerStatus(null);
      setNotice(`Stop gagal: ${error instanceof Error ? error.message : "Unknown error"}`); 
    } 
  };
  const saveSettings = async () => {
    setSaving(true);
    try {
      const saved = await terminalApi.saveConfiguration(config, { symbol, timeframe, strategy: "Evidence trend guard", riskPerTrade: risk, dailyLossLimit: dailyLoss, paperMode, robotControls: { enabled: botStatus === "RUNNING", lotSize, stopLossPips: stopLoss, takeProfitPips: takeProfit } });
      applyConfig(saved); setSettingsOpen(false); setNotice("Trading Rules tersimpan.");
    } catch (error) { setNotice(`Gagal menyimpan: ${error instanceof Error ? error.message : "Unknown error"}`); }
    finally { setSaving(false); }
  };

  return <div className="min-h-screen bg-[#080b12] p-3 font-mono text-slate-200 lg:h-screen lg:overflow-hidden">
    <div className="grid min-h-[calc(100vh-24px)] gap-3 lg:h-[calc(100vh-24px)] lg:grid-cols-[230px_minmax(420px,1fr)_320px]">
      <aside className="terminal-panel flex flex-col p-4">
        <h2 className="terminal-title">CONTROL PANEL</h2><Status connected={Boolean(snapshot?.connected)} botStatus={botStatus} account={snapshot?.account ? String(snapshot.account.login) : ""} />
        <div className="mt-4 grid grid-cols-1 gap-2">
          {botStatus === "RUNNING" ? (
            <button onClick={stopBot} className="terminal-button bg-rose-400 text-slate-950 hover:bg-rose-500 active:scale-[0.98] transition-all">
              <Square className="h-3.5 w-3.5 mr-2" /> STOP AUTO TRADE
            </button>
          ) : (
            <button 
              onClick={startBot} 
              disabled={!snapshot?.connected || !config} 
              className={`terminal-button bg-emerald-300 text-slate-950 hover:bg-emerald-400 active:scale-[0.98] transition-all ${!snapshot?.connected || !config ? 'opacity-40 cursor-not-allowed' : ''}`}
            >
              <Play className="h-3.5 w-3.5 mr-2" /> START AUTO TRADE
            </button>
          )}
          {!snapshot?.connected && <p className="text-xs text-center text-rose-400 mt-1">âš ï¸ MT5 terminal belum terhubung</p>}
          {!config && botStatus === "STOPPED" && <p className="text-xs text-center text-amber-400 mt-1">ðŸ’¾ Simpan Trading Rules terlebih dahulu</p>}
        </div>
        <button onClick={() => setSettingsOpen(true)} className="terminal-button mt-3 bg-amber-200 text-slate-950"><Settings className="h-3.5 w-3.5" /> SETTINGS</button>
        <Control label="SYMBOL"><select value={symbol} onChange={(event) => setSymbol(event.target.value)}><option>XAUUSD</option><option>GOLD</option></select></Control>
        <Control label="TIMEFRAME"><select value={timeframe} onChange={(event) => setTimeframe(event.target.value)}><option>M5</option><option>M15</option><option>M30</option><option>H1</option></select></Control>
        <MetricBlock label="NEXT CYCLE" value={nextCycle} detail={`Candle close Â· ${timeframe}`} accent />
        <MetricBlock label="ACCOUNT" value={snapshot?.account ? String(snapshot.account.login) : "OFFLINE"} detail={snapshot?.account ? `${snapshot.account.server} Â· ${snapshot.account.is_demo ? "DEMO" : "LIVE"}` : "MT5 terminal unavailable"} />
        <MetricBlock label="FLOATING P&L" value={`${snapshot?.account?.currency || "$"} ${(snapshot?.positions.reduce((sum, position) => sum + Number(position.profit || 0), 0) || 0).toFixed(2)}`} valueClass={(snapshot?.positions.reduce((sum, position) => sum + Number(position.profit || 0), 0) || 0) >= 0 ? "text-emerald-300" : "text-rose-400"} />
        <div className="terminal-inset mt-3 p-3 text-xs"><p className="terminal-title mb-2">PERFORMANCE</p><Row label="Win Rate" value={executed.length ? `${((wins / executed.length) * 100).toFixed(1)}%` : "0.0%"} /><Row label="Trades" value={String(executed.length)} /><Row label="Profit Factor" value="0.00" /></div>
        <div className="mt-auto pt-3 text-[10px] text-slate-500"><ShieldCheck className="mr-1 inline h-3 w-3 text-emerald-400" />Risk gate dan daily loss limit aktif.</div>
      </aside>
      <main className="grid min-h-0 gap-3 lg:grid-rows-[minmax(300px,1.4fr)_minmax(220px,1fr)_150px]">
        <section className="terminal-panel min-h-0 p-3"><header className="flex items-center justify-between"><div><h2 className="terminal-title">MARKET CHART (REALTIME MT5)</h2><p className="mt-1 text-xs text-slate-500">{snapshot?.symbol || symbol} Â· {timeframe} Â· {snapshot ? `Bid ${snapshot.quote.bid} / Ask ${snapshot.quote.ask}` : "OFFLINE"}</p></div><strong className="text-lg">{latest?.close.toFixed(2) ?? "--"}</strong></header><div className="h-[calc(100%-42px)]"><TerminalChart bars={bars} symbol={symbol} timeframe={timeframe} /></div></section>
         <section className="terminal-panel min-h-0 overflow-hidden p-4"><h2 className="terminal-title">AI SIGNAL & MATH CALC</h2><div className="mt-3 flex items-end justify-between"><strong className={`text-4xl ${runnerStatus?.lastDecision === "BUY" ? "text-emerald-300" : runnerStatus?.lastDecision === "SELL" ? "text-rose-400" : "text-slate-400"}`}>{runnerStatus?.lastDecision || "HOLD"}</strong><span className="text-xs text-slate-400">Engine: {runnerStatus?.state === "RUNNING" ? "LIVE" : runnerStatus?.state === "ERROR" ? "ERROR" : "STANDBY"}</span></div><div className="mt-4 grid grid-cols-4 gap-4 text-xs"><Quote label="Entry" value={signal?.price} /><Quote label="SL" value={signal?.stopLoss} danger /><Quote label="TP" value={signal?.takeProfit} positive /><Quote label="Order" value={runnerStatus?.lastOrderId ? Number(runnerStatus.lastOrderId) : null} /></div><pre className="terminal-inset mt-4 max-h-28 overflow-auto whitespace-pre-wrap p-3 text-[10px] leading-5 text-slate-400">{`STRATEGY: ${runnerStatus?.selectedStrategyId || "adaptive selector"}\nMODE: Demo only Â· chart-only area ranking\nSTATE: ${runnerStatus?.state || "IDLE"}\nLAST CANDLE: ${runnerStatus?.lastCandleAt || "-"}\nDECISION: ${runnerStatus?.lastDecision || "-"}\nMESSAGE: ${runnerStatus?.message || "Tekan START untuk mulai."}${runnerStatus?.lastError ? "\nERROR: " + runnerStatus.lastError : ""}`}</pre><CandidateRankingPanel candidates={runnerStatus?.entryAreaCandidates || []} selectedId={runnerStatus?.selectedEntryAreaId} /></section>
        <section className="terminal-panel p-3"><h2 className="terminal-title">P&L CURVE (ALL-TIME)</h2><div className="mt-4 h-20 border-b border-l border-slate-800"><svg className="h-full w-full" viewBox="0 0 600 80" preserveAspectRatio="none"><polyline fill="none" stroke="#e96b86" strokeWidth="2" points="0,20 100,25 200,29 300,38 400,43 500,55 600,60" /></svg></div></section>
      </main>
      <aside className="grid min-h-0 gap-3 lg:grid-rows-[200px_220px_minmax(260px,1fr)]"><PositionPanel rows={openPositions} /><HistoryPanel rows={snapshot?.executions || []} /><section className="terminal-panel min-h-0 p-3"><h2 className="terminal-title">SYSTEM LOGS (LIVE)</h2><div className="mt-3 h-[calc(100%-24px)] overflow-auto text-[10px] leading-5"><p className={snapshot ? "text-emerald-300" : "text-rose-400"}>[{new Date().toLocaleTimeString()}] {notice}</p>{logs.map((log) => <p key={log.id}><span className="text-slate-600">[{new Date(log.timestamp).toLocaleTimeString()}]</span> <span className={log.level === "ERROR" || log.level === "RISK" ? "text-rose-400" : log.level === "SIGNAL" ? "text-amber-300" : "text-cyan-400"}>[{log.level}]</span> {log.message}</p>)}</div></section></aside>
    </div>
    <div className="pointer-events-none fixed bottom-4 left-1/2 z-30 -translate-x-1/2 rounded border border-slate-700 bg-slate-950/95 px-4 py-2 text-xs shadow-xl">{notice}</div>
    {settingsOpen && <SettingsModal values={{ lotSize, stopLoss, takeProfit, risk, dailyLoss, paperMode }} setters={{ setLotSize, setStopLoss, setTakeProfit, setRisk, setDailyLoss, setPaperMode }} token={mcpToken} onToken={setMcpToken} connected={Boolean(snapshot)} onClose={() => setSettingsOpen(false)} onSave={saveSettings} saving={saving} />}
  </div>;
}

function Status({ connected, botStatus, account }: { connected: boolean; botStatus: BotStatus; account: string }) { return <div className="mt-4 space-y-2 text-xs"><p className={connected ? "text-emerald-300" : "text-rose-400"}>{connected ? <Wifi className="mr-2 inline h-3.5 w-3.5" /> : <WifiOff className="mr-2 inline h-3.5 w-3.5" />}MT5: {connected ? `CONNECTED (${account})` : "OFFLINE"}</p><p className={botStatus === "RUNNING" ? "text-emerald-300" : "text-slate-500"}><span className="mr-2">â—</span>BOT: {botStatus}</p></div>; }
function Control({ label, children }: { label: string; children: React.ReactNode }) { return <label className="mt-4 block text-[10px] text-slate-500">{label}<div className="terminal-select mt-1">{children}</div></label>; }
function MetricBlock({ label, value, detail, accent, valueClass = "" }: { label: string; value: string; detail?: string; accent?: boolean; valueClass?: string }) { return <div className="terminal-inset mt-3 p-3"><p className="terminal-title">{label}</p><p className={`mt-2 text-xl font-semibold ${accent ? "text-blue-300" : ""} ${valueClass}`}>{value}</p>{detail && <p className="mt-1 text-[9px] text-slate-600">{detail}</p>}</div>; }
function Row({ label, value }: { label: string; value: string }) { return <p className="flex justify-between py-1"><span className="text-slate-500">{label}</span><span>{value}</span></p>; }
function Quote({ label, value, danger, positive }: { label: string; value: number | null | undefined; danger?: boolean; positive?: boolean }) { return <div><p className="text-slate-500">{label}</p><strong className={danger ? "text-rose-400" : positive ? "text-emerald-300" : ""}>{value?.toFixed(2) ?? "0.00"}</strong></div>; }
function CandidateRankingPanel({ candidates, selectedId }: { candidates: AutoTradeEntryAreaCandidate[]; selectedId: string | null | undefined }) {
  return <div className="terminal-inset mt-3 min-h-0 overflow-hidden p-3"><div className="flex items-center justify-between"><p className="terminal-title">ENTRY AREA RANKING</p><span className="text-[9px] text-slate-600">CHART-ONLY</span></div><div className="mt-2 max-h-24 overflow-auto text-[10px]">{candidates.map((candidate, index) => <div key={candidate.id} className={`grid grid-cols-[18px_1fr_auto] gap-2 border-t border-slate-800/70 py-1.5 ${candidate.id === selectedId ? "text-amber-200" : ""}`}><span className="text-slate-600">{index + 1}</span><span><strong>{candidate.type}</strong> <span className="text-slate-500">{candidate.direction === "BULLISH" ? "BUY" : "SELL"} · {candidate.reactionStatus.replace(/_/g, " ")}{candidate.liquiditySweep ? " · SWEEP" : ""}</span></span><span className="text-right">{candidate.score.toFixed(2)}</span></div>)}{!candidates.length && <p className="py-3 text-center text-slate-600">Belum ada kandidat area</p>}</div></div>;
}
function PositionPanel({ rows }: { rows: Mt5Position[] }) { return <section className="terminal-panel min-h-0 overflow-hidden p-3"><h2 className="terminal-title">OPEN POSITIONS</h2><div className="mt-3 h-[calc(100%-22px)] overflow-auto"><table className="w-full text-[10px]"><thead className="text-slate-600"><tr><th className="text-left">Symbol</th><th>Type</th><th>Lot</th><th className="text-right">Profit</th></tr></thead><tbody>{rows.map((row) => <tr key={String(row.ticket)} className="border-t border-slate-800/70"><td className="py-2">{row.symbol}</td><td className={row.side === "buy" ? "text-center text-emerald-300" : "text-center text-rose-400"}>{row.side.toUpperCase()}</td><td className="text-center">{Number(row.volume).toFixed(2)}</td><td className={`text-right ${Number(row.profit) >= 0 ? "text-emerald-300" : "text-rose-400"}`}>{Number(row.profit).toFixed(2)}</td></tr>)}</tbody></table>{!rows.length && <p className="mt-8 text-center text-[10px] text-slate-600">Tidak ada posisi terbuka</p>}</div></section>; }
function HistoryPanel({ rows }: { rows: Mt5LiveSnapshot["executions"] }) { return <section className="terminal-panel min-h-0 overflow-hidden p-3"><h2 className="terminal-title">TRADE HISTORY (7D)</h2><div className="mt-3 h-[calc(100%-22px)] overflow-auto"><table className="w-full text-[10px]"><thead className="text-slate-600"><tr><th className="text-left">Time</th><th>Symbol</th><th>Lot</th><th className="text-right">Profit</th></tr></thead><tbody>{rows.slice().reverse().map((row) => <tr key={row.deal_id} className="border-t border-slate-800/70"><td className="py-2">{new Date(row.time * 1000).toLocaleTimeString()}</td><td className="text-center">{row.symbol}</td><td className="text-center">{Number(row.volume).toFixed(2)}</td><td className={`text-right ${Number(row.profit) >= 0 ? "text-emerald-300" : "text-rose-400"}`}>{Number(row.profit).toFixed(2)}</td></tr>)}</tbody></table>{!rows.length && <p className="mt-8 text-center text-[10px] text-slate-600">Belum ada deal</p>}</div></section>; }

type ModalValues = { lotSize: number; stopLoss: number; takeProfit: number; risk: number; dailyLoss: number; paperMode: boolean };
type ModalSetters = { setLotSize: (value: number) => void; setStopLoss: (value: number) => void; setTakeProfit: (value: number) => void; setRisk: (value: number) => void; setDailyLoss: (value: number) => void; setPaperMode: (value: boolean) => void };
function NumField({ label, value, onChange, min, max, step }: { label: string; value: number; onChange: (v: number) => void; min: number; max: number; step: number }) {
  const decimals = step < 1 ? (step.toString().split(".")[1] || "").length : 0;
  // `draft` menyimpan teks mentah supaya user bisa mengetik bebas (termasuk
  // kosong / nilai sementara di luar range seperti "3" pada field min 5).
  // Clamp ke min/max hanya dilakukan saat blur atau tombol +/-.
  const [draft, setDraft] = useState<string | null>(null);
  const clamp = (n: number) => Math.min(max, Math.max(min, Number(n.toFixed(decimals))));
  const commit = () => {
    if (draft === null) return;
    const parsed = Number(draft);
    onChange(draft.trim() === "" || isNaN(parsed) ? value : clamp(parsed));
    setDraft(null);
  };
  const nudge = (delta: number) => { setDraft(null); onChange(clamp(value + delta)); };
  return (
    <label className="text-[10px] text-slate-500">{label}
      <div className="mt-1 flex items-center gap-1">
        <button type="button" onClick={() => nudge(-step)} className="terminal-button bg-slate-700 text-slate-200 h-7 w-7 text-xs font-bold">−</button>
        <input
          type="number" min={min} max={max} step={step}
          value={draft ?? String(value)}
          onChange={(event) => {
            const raw = event.target.value;
            setDraft(raw);
            const parsed = Number(raw);
            if (raw.trim() !== "" && !isNaN(parsed) && parsed >= min && parsed <= max) onChange(Number(parsed.toFixed(decimals)));
          }}
          onBlur={commit}
          onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); commit(); } }}
          className="terminal-input flex-1 text-center"
        />
        <button type="button" onClick={() => nudge(step)} className="terminal-button bg-slate-700 text-slate-200 h-7 w-7 text-xs font-bold">+</button>
      </div>
    </label>
  );
}

function SettingsModal({ values, setters, token, onToken, connected, onClose, onSave, saving }: { values: ModalValues; setters: ModalSetters; token: McpToken | null; onToken: (token: McpToken | null) => void; connected: boolean; onClose: () => void; onSave: () => void; saving: boolean }) {
  const { lotSize, stopLoss, takeProfit, risk, dailyLoss, paperMode } = values;
  const { setLotSize, setStopLoss, setTakeProfit, setRisk, setDailyLoss, setPaperMode } = setters;
  const endpoint = `${window.location.protocol}//${window.location.hostname}:8899/mt5`;
  const [mt5, setMt5] = useState<Mt5ConfigurationInput>({ login: 0, password: "", server: "", terminalPath: "", profile: "paper", symbolSuffix: "", timeout: 15, maxOrderVolume: 1, maxOrderNotionalUsd: 10_000 });
  const [mt5Message, setMt5Message] = useState("Memuat konfigurasiâ€¦");
  useEffect(() => { terminalApi.mt5Configuration().then((value) => { setMt5({ login: value.login, password: "", server: value.server, terminalPath: value.terminalPath, profile: value.profile, symbolSuffix: value.symbolSuffix, timeout: value.timeout, maxOrderVolume: value.maxOrderVolume, maxOrderNotionalUsd: value.maxOrderNotionalUsd }); setMt5Message(value.passwordConfigured ? `Password tersimpan Â· ${value.configPath}` : `Password belum diisi Â· ${value.configPath}`); }).catch((error) => setMt5Message(error instanceof Error ? error.message : "Gagal memuat konfigurasi")); }, []);
  const saveMt5 = async () => { try { const saved = await terminalApi.saveMt5Configuration(mt5); setMt5Message(`Tersimpan di ${saved.configPath}. Dashboard sedang mencoba reconnectâ€¦`); } catch (error) { setMt5Message(error instanceof Error ? error.message : "Gagal menyimpan konfigurasi MT5"); } };
  const generate = async () => { try { onToken(await terminalApi.generateMcpToken(168)); } catch { onToken(null); } };
  const revoke = async () => { if (!token) return; await terminalApi.revokeMcpToken(token.tokenId); onToken(null); };
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"><div className="terminal-panel max-h-[92vh] w-full max-w-2xl overflow-auto p-5"><header className="flex items-center justify-between"><div><h2 className="text-sm font-semibold">AUTO TRADE SETTINGS</h2><p className="mt-1 text-[10px] text-slate-500">Isi koneksi MT5 di dashboard web ini. MCP hanya untuk EA bridge.</p></div><button onClick={onClose}><X className="h-4 w-4" /></button></header><section className="terminal-inset mt-5 p-4"><div className="flex items-center justify-between"><h3 className="terminal-title">1 Â· MT5 CONNECTION (REALTIME MARKET)</h3><span className={connected ? "text-[10px] text-emerald-300" : "text-[10px] text-rose-400"}>{connected ? "CONNECTED" : "OFFLINE"}</span></div><div className="mt-3 grid grid-cols-2 gap-3"><Mt5Field label="Login" type="number" value={mt5.login || ""} onChange={(value) => setMt5({ ...mt5, login: Number(value) })} /><Mt5Field label="Password" type="password" value={mt5.password} placeholder="Kosong = gunakan password tersimpan" onChange={(value) => setMt5({ ...mt5, password: value })} /><Mt5Field label="Broker server" value={mt5.server} placeholder="Contoh: Exness-MT5Trial8" onChange={(value) => setMt5({ ...mt5, server: value })} /><label className="text-[10px] text-slate-500">Account profile<select className="terminal-input mt-1" value={mt5.profile} onChange={(event) => setMt5({ ...mt5, profile: event.target.value as Mt5ConfigurationInput["profile"] })}><option value="paper">Demo / Paper</option><option value="live-readonly">Live Â· Read only</option><option value="live">Live Â· Trading</option></select></label><Mt5Field label="Terminal path (optional)" value={mt5.terminalPath} placeholder="C:\Program Files\MetaTrader 5\terminal64.exe" onChange={(value) => setMt5({ ...mt5, terminalPath: value })} /><Mt5Field label="Symbol suffix (optional)" value={mt5.symbolSuffix} placeholder="Contoh: m" onChange={(value) => setMt5({ ...mt5, symbolSuffix: value })} /></div><p className="mt-3 text-[9px] text-slate-500">{mt5Message}</p><button onClick={saveMt5} disabled={!mt5.login || !mt5.server} className="terminal-button mt-3 bg-emerald-300 text-slate-950 disabled:opacity-40">Save MT5 connection</button></section><section className="terminal-inset mt-4 p-4"><h3 className="terminal-title">2 Â· MCP / EA BRIDGE (OPTIONAL)</h3><p className="mt-2 text-[9px] text-slate-500">Gunakan ini hanya bila Anda memasang EA bridge di chart MT5. Untuk realtime chart direct, bagian ini boleh dilewati.</p><label className="mt-3 block text-[10px] text-slate-500">Backend endpoint<input readOnly value={endpoint} className="terminal-input mt-1" /></label><div className="mt-3">{token ? <><input readOnly value={token.tokenId} className="terminal-input text-amber-200" /><p className="mt-1 text-[9px] text-slate-600">Salin ke input token EA bridge. Kedaluwarsa {new Date(token.expiresAt).toLocaleString()}.</p><button onClick={revoke} className="terminal-button mt-2 border border-rose-500/50 text-rose-300">Revoke token</button></> : <button onClick={generate} className="terminal-button bg-cyan-300 text-slate-950">Generate MCP token</button>}</div></section><section><h3 className="terminal-title mt-5">3 · TRADING RULES</h3><div className="mt-3 grid grid-cols-2 gap-3">
          <NumField label="Lot size" value={lotSize} onChange={setLotSize} min={0.01} max={1} step={0.01} />
          <NumField label="Stop Loss (pips)" value={stopLoss} onChange={setStopLoss} min={5} max={250} step={1} />
          <NumField label="Take Profit (pips)" value={takeProfit} onChange={setTakeProfit} min={10} max={500} step={1} />
          <NumField label="Risk / trade (%)" value={risk} onChange={setRisk} min={0.01} max={5} step={0.01} />
          <NumField label="Daily loss limit (%)" value={dailyLoss} onChange={setDailyLoss} min={0.1} max={20} step={0.1} />
        </div><label className="mt-4 flex items-center gap-2 text-xs"><input type="checkbox" checked={paperMode} onChange={(event) => setPaperMode(event.target.checked)} /> Paper mode (disarankan)</label></section><div className="mt-5 flex justify-end gap-2"><button onClick={onClose} className="terminal-button border border-slate-700">Tutup</button><button onClick={onSave} disabled={saving} className="terminal-button bg-amber-200 text-slate-950 disabled:opacity-50">{saving ? "Menyimpanâ€¦" : "Simpan rules"}</button></div></div></div>;
}

function Mt5Field({ label, value, onChange, type = "text", placeholder = "" }: { label: string; value: string | number; onChange: (value: string) => void; type?: string; placeholder?: string }) { return <label className="text-[10px] text-slate-500">{label}<input type={type} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} className="terminal-input mt-1" /></label>; }
