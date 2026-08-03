import { Calculator, ShieldCheck } from "lucide-react";
import { useState } from "react";

const XAUUSD_PIP_SIZE = 0.1;
const PIP_VALUE_PER_LOT = 10;
const LOT_STEP = 0.01;

export function InteractiveLotCalculator({ defaultEntry, defaultStopLoss }: { defaultEntry: number; defaultStopLoss: number }) {
  const [balance, setBalance] = useState("10000");
  const [riskPercent, setRiskPercent] = useState("1");
  const [entry, setEntry] = useState(defaultEntry.toFixed(5));
  const [stopLoss, setStopLoss] = useState(defaultStopLoss.toFixed(5));
  const balanceValue = Number(balance);
  const riskValue = Number(riskPercent);
  const entryValue = Number(entry);
  const stopLossValue = Number(stopLoss);
  const stopDistance = Math.abs(entryValue - stopLossValue);
  const stopPips = stopDistance / XAUUSD_PIP_SIZE;
  const riskAmount = balanceValue * (riskValue / 100);
  const rawLot = riskAmount / (stopPips * PIP_VALUE_PER_LOT);
  const lotSize = Math.floor(rawLot / LOT_STEP) * LOT_STEP;
  const valid = Number.isFinite(lotSize) && balanceValue >= 100 && riskValue >= 1 && riskValue <= 2 && stopPips > 0;

  return <article className="overflow-hidden rounded-xl border bg-card shadow-sm" aria-label="Interactive lot calculator">
    <div className="flex items-start gap-3 border-b p-5"><span className="rounded-lg bg-sky-500/10 p-2 text-sky-500"><Calculator className="h-4 w-4" /></span><div><h2 className="font-semibold">Interactive lot sizer</h2><p className="mt-0.5 text-xs text-muted-foreground">Size XAUUSD exposure from account risk and the mechanical stop distance.</p></div></div>
    <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,1.15fr)_minmax(260px,0.85fr)]"><form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => event.preventDefault()}><Field label="Account balance (USD)" value={balance} onChange={setBalance} min="100" step="100" /><label className="block"><span className="text-xs font-medium">Risk per trade</span><select aria-label="Risk per trade" value={riskPercent} onChange={(event) => setRiskPercent(event.target.value)} className="mt-1.5 w-full rounded-lg border bg-background px-3 py-2.5 text-sm outline-none focus:border-primary"><option value="1">1.0%</option><option value="1.5">1.5%</option><option value="2">2.0%</option></select></label><Field label="Entry price" value={entry} onChange={setEntry} min="0.00001" step="0.00001" /><Field label="Stop loss price" value={stopLoss} onChange={setStopLoss} min="0.00001" step="0.00001" /></form><div className={`rounded-xl border p-5 ${valid ? "border-emerald-500/30 bg-emerald-500/5" : "border-rose-500/30 bg-rose-500/5"}`}><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Calculated position size</p><p className={`mt-2 font-mono text-4xl font-bold ${valid ? "text-emerald-500" : "text-rose-500"}`}>{valid ? lotSize.toFixed(2) : "--"} <span className="text-sm">lot</span></p><div className="mt-4 space-y-2 text-xs"><Row label="Risk amount" value={valid ? `$${riskAmount.toFixed(2)}` : "--"} /><Row label="Stop distance" value={valid ? `${stopPips.toFixed(1)} pips` : "--"} /><Row label="Pip value / lot" value="$10.00" /></div><div className="mt-4 flex items-start gap-2 border-t pt-3 text-[10px] text-muted-foreground"><ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" /><p>{valid ? "Rounded down to the 0.01 lot step so estimated risk is not exceeded." : "Enter a balance of at least $100 and different entry/SL prices."}</p></div><p className="mt-3 text-right text-[9px] uppercase tracking-wider text-muted-foreground">Preview calculation · verify broker contract specs</p></div></div>
  </article>;
}

function Field({ label, value, onChange, min, step }: { label: string; value: string; onChange: (value: string) => void; min: string; step: string }) { return <label className="block"><span className="text-xs font-medium">{label}</span><input aria-label={label} type="number" value={value} onChange={(event) => onChange(event.target.value)} min={min} step={step} className="mt-1.5 w-full rounded-lg border bg-background px-3 py-2.5 font-mono text-sm outline-none focus:border-primary" /></label>; }
function Row({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-3"><span className="text-muted-foreground">{label}</span><strong className="font-mono">{value}</strong></div>; }
