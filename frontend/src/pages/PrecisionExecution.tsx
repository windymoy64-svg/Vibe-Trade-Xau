import { useState } from "react";
import { ArrowLeft, BarChart3, CheckCircle2, Crosshair, Database, Play, ShieldAlert, Target } from "lucide-react";
import { Link } from "react-router";
import { actionableSignalPreview, acrZonePreview, fibonacciValuationPreview, htfStructurePreview, ltfSupplyDemandPreview, orderTypeRecommendationPreview, precisionEntryPreview, precisionExecutionPreview, tradeLevelsPreview, trailingStopPreview, type PrecisionWorkflowStatus } from "@/data/precision-execution";
import { OhlcFileUpload } from "@/components/precision-execution/OhlcFileUpload";
import { HtfStructureChart } from "@/components/precision-execution/HtfStructureChart";
import { LtfSupplyDemandChart } from "@/components/precision-execution/LtfSupplyDemandChart";
import { AcrZonesPanel } from "@/components/precision-execution/AcrZonesPanel";
import { FibonacciValuationPanel } from "@/components/precision-execution/FibonacciValuationPanel";
import { OrderTypeRecommendation } from "@/components/precision-execution/OrderTypeRecommendation";
import { PrecisionEntryPrice } from "@/components/precision-execution/PrecisionEntryPrice";
import { StopLossTakeProfitPanel } from "@/components/precision-execution/StopLossTakeProfitPanel";
import { TrailingStopVisualization } from "@/components/precision-execution/TrailingStopVisualization";
import { ActionableSignalCard } from "@/components/precision-execution/ActionableSignalCard";
import { InteractiveLotCalculator } from "@/components/precision-execution/InteractiveLotCalculator";

const workflowTone: Record<PrecisionWorkflowStatus, string> = {
  COMPLETE: "bg-emerald-500/10 text-emerald-500",
  ACTIVE: "bg-amber-500/10 text-amber-500",
  WAITING: "bg-muted text-muted-foreground",
};

export function PrecisionExecution() {
  const [symbol, setSymbol] = useState(precisionExecutionPreview.symbol);
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const generatedAt = analysisStarted ? new Date().toISOString() : precisionExecutionPreview.generatedAt;

  return <div className="mx-auto max-w-7xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
      <div><Link to="/auto-trade" className="mb-4 inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"><ArrowLeft className="h-3.5 w-3.5" /> Auto Trade</Link><div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary"><Crosshair className="h-4 w-4" /> ACR / SMC execution terminal <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] tracking-normal text-amber-500">Preview only</span></div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Precision trading execution</h1><p className="mt-1 max-w-2xl text-sm text-muted-foreground">Map HTF structure, validate ACR/FVG confluence, and stage an evidence-based execution plan from OHLC data.</p></div>
      <div className="flex flex-col items-stretch gap-2 sm:items-end"><button type="button" onClick={() => setAnalysisStarted(true)} disabled={analysisStarted} className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-default disabled:bg-emerald-600"><span className="sr-only">Preview only. </span>{analysisStarted ? <CheckCircle2 className="h-4 w-4" /> : <Play className="h-4 w-4" />} {analysisStarted ? "Analysis extracted" : "Mulai Ekstrak / Analisis Strategy"}</button>{analysisStarted && <p role="status" className="text-right text-[10px] text-emerald-500">Preview analysis complete · no order routed</p>}</div>
    </header>

    <section className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
      <article className="rounded-xl border bg-card shadow-sm"><PanelTitle icon={Database} title="Market data input" detail="Choose the preview instrument and inspect the active OHLC source." /><div className="grid gap-4 p-5 sm:grid-cols-3"><label className="block"><span className="text-xs font-medium">Instrument</span><select value={symbol} onChange={(event) => setSymbol(event.target.value)} className="mt-1.5 w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:border-primary"><option>XAUUSD</option><option>EURUSD</option><option>GBPUSD</option></select></label><DataField label="HTF / LTF" value={`${precisionExecutionPreview.htfTimeframe} / ${precisionExecutionPreview.ltfTimeframe}`} /><DataField label="Data coverage" value={precisionExecutionPreview.dataSource} /></div><OhlcFileUpload /><div className="border-t px-5 py-3 text-right text-xs text-muted-foreground">Evaluated {new Date(generatedAt).toLocaleString()}</div></article>
      <article className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-5"><div className="flex gap-3"><ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" /><div><h2 className="text-sm font-semibold">No live order routing</h2><p className="mt-1 text-xs leading-relaxed text-muted-foreground">Analysis updates page state only. Entry, cancel, exit, SL and TP values cannot reach a broker.</p></div></div></article>
    </section>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{precisionExecutionPreview.workflow.map((step, index) => <article key={step.id} className="rounded-xl border bg-card p-4"><div className="flex items-start justify-between gap-3"><span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted font-mono text-xs font-semibold">{index + 1}</span><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${workflowTone[analysisStarted && step.status === "WAITING" && index === 2 ? "ACTIVE" : step.status]}`}>{analysisStarted && step.status === "WAITING" && index === 2 ? "ACTIVE" : step.status}</span></div><h2 className="mt-4 text-sm font-semibold">{step.label}</h2><p className="mt-1 text-xs text-muted-foreground">{step.detail}</p></article>)}</section>

    <ActionableSignalCard signal={actionableSignalPreview} />

    <section className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
      <article className="rounded-xl border bg-card shadow-sm"><PanelTitle icon={BarChart3} title="HTF structure chart" detail={`${symbol} ${precisionExecutionPreview.htfTimeframe} candles with confirmed structure events.`} /><div className="flex flex-wrap gap-2 px-5 pt-4 text-[10px]"><span className="rounded-full bg-emerald-500/10 px-2 py-1 text-emerald-500">BOS · continuation break</span><span className="rounded-full bg-amber-500/10 px-2 py-1 text-amber-500">CHOCH · structure shift</span><span className="ml-auto text-muted-foreground">{htfStructurePreview.markers.length} markers</span></div><div className="p-3"><HtfStructureChart candles={htfStructurePreview.candles} markers={htfStructurePreview.markers} /></div></article>
      <article className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 shadow-sm"><PanelTitle icon={Target} title="Current setup preview" detail="Latest actionable plan from the mock analysis." /><div className="space-y-4 p-5"><div className="flex items-center justify-between"><div><p className="text-xs text-muted-foreground">Bias</p><p className="mt-1 font-mono text-xl font-semibold text-emerald-500">{precisionExecutionPreview.bias}</p></div><span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-500">{precisionExecutionPreview.setup.status}</span></div><div className="grid grid-cols-2 gap-3"><SetupMetric label="Direction" value={precisionExecutionPreview.setup.direction} tone="text-emerald-500" /><SetupMetric label="Order type" value={precisionExecutionPreview.setup.executionMethod} tone="text-amber-500" /><SetupMetric label="Entry" value={precisionExecutionPreview.setup.entry.toFixed(2)} /><SetupMetric label="Stop loss" value={precisionExecutionPreview.setup.stopLoss.toFixed(2)} tone="text-rose-500" /></div><div className="flex items-center justify-between rounded-lg border border-emerald-500/20 bg-background/70 p-3 text-xs"><span className="text-muted-foreground">Minimum RRR</span><strong>1:{precisionExecutionPreview.setup.riskReward.toFixed(1)}</strong></div></div></article>
    </section>

    <section className="rounded-xl border bg-card shadow-sm">
      <PanelTitle icon={Crosshair} title="LTF Supply / Demand map" detail={`${symbol} ${precisionExecutionPreview.ltfTimeframe} execution zones from the preview structure scan.`} />
      <div className="grid gap-3 border-b p-5 sm:grid-cols-2">
        {ltfSupplyDemandPreview.zones.map((zone) => <div key={zone.id} className={`rounded-lg border p-3 ${zone.type === "SUPPLY" ? "border-rose-500/30 bg-rose-500/5" : "border-emerald-500/30 bg-emerald-500/5"}`}><div className="flex items-center justify-between gap-3"><strong className={`text-xs ${zone.type === "SUPPLY" ? "text-rose-500" : "text-emerald-500"}`}>{zone.type}</strong><span className="rounded-full bg-background px-2 py-0.5 text-[9px] font-semibold text-muted-foreground">{zone.status}</span></div><p className="mt-2 font-mono text-sm">{zone.low.toFixed(2)} - {zone.high.toFixed(2)}</p></div>)}
      </div>
      <div className="flex flex-wrap items-center gap-2 px-5 pt-4 text-[10px]"><span className="rounded-full bg-emerald-500/10 px-2 py-1 text-emerald-500">Bullish R-ACR · low sweep + reclaim</span><span className="rounded-full bg-rose-500/10 px-2 py-1 text-rose-500">Bearish R-ACR · high sweep + reject</span><span className="rounded-full bg-sky-500/10 px-2 py-1 text-sky-500">Bullish FVG · open</span><span className="rounded-full bg-amber-500/10 px-2 py-1 text-amber-500">Bearish FVG · partial</span><span className="ml-auto text-muted-foreground">{ltfSupplyDemandPreview.reversalMarkers.length} reversal markers · {ltfSupplyDemandPreview.fvgZones.filter((zone) => zone.acrConfluence).length} FVG confluence</span></div>
      {ltfSupplyDemandPreview.fvgZones.filter((zone) => zone.acrConfluence).map((zone) => <div key={`${zone.id}-confluence`} className="mx-5 mt-3 flex flex-col justify-between gap-2 rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-xs sm:flex-row sm:items-center"><div><strong className="text-amber-500">HIGH CONFLUENCE · FVG + ACR</strong><p className="mt-1 text-[10px] text-muted-foreground">{zone.direction} imbalance overlaps fresh zone {zone.acrZoneId}.</p></div><span className="font-mono font-semibold">{zone.overlapLow?.toFixed(2)} - {zone.overlapHigh?.toFixed(2)}</span></div>)}
      <div className="p-3"><LtfSupplyDemandChart candles={ltfSupplyDemandPreview.candles} zones={ltfSupplyDemandPreview.zones} reversalMarkers={ltfSupplyDemandPreview.reversalMarkers} fvgZones={ltfSupplyDemandPreview.fvgZones} /></div>
    </section>

    <section className="space-y-3"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Strict OHLC detection</p><h2 className="mt-1 text-lg font-semibold">Active ACR zones</h2><p className="mt-1 text-xs text-muted-foreground">Standard bullish and bearish zones derived from the latest M15 candle closes.</p></div><AcrZonesPanel zones={acrZonePreview} /></section>

    <FibonacciValuationPanel valuation={fibonacciValuationPreview} />

    <OrderTypeRecommendation recommendation={orderTypeRecommendationPreview} />

    <PrecisionEntryPrice entry={precisionEntryPreview} />

    <StopLossTakeProfitPanel levels={tradeLevelsPreview} />

    <TrailingStopVisualization trailing={trailingStopPreview} />

    <InteractiveLotCalculator defaultEntry={precisionEntryPreview.price} defaultStopLoss={tradeLevelsPreview.stopLoss} />
  </div>;
}

function PanelTitle({ icon: Icon, title, detail }: { icon: typeof Database; title: string; detail: string }) { return <div className="flex items-start gap-3 border-b p-5"><span className="rounded-lg bg-primary/10 p-2 text-primary"><Icon className="h-4 w-4" /></span><div><h2 className="font-semibold">{title}</h2><p className="mt-0.5 text-xs text-muted-foreground">{detail}</p></div></div>; }
function DataField({ label, value }: { label: string; value: string }) { return <div><p className="text-xs font-medium">{label}</p><div className="mt-1.5 flex min-h-10 items-center rounded-lg border bg-muted/30 px-3 text-xs text-muted-foreground">{value}</div></div>; }
function SetupMetric({ label, value, tone = "text-foreground" }: { label: string; value: string; tone?: string }) { return <div className="rounded-lg bg-background/70 p-3"><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p><p className={`mt-1 font-mono text-sm font-semibold ${tone}`}>{value}</p></div>; }
