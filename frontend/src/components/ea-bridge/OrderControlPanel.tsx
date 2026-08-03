import { useState } from "react";
import { AlertTriangle, CircleX, LockKeyhole, Minus, Pencil, Plus, ShoppingCart } from "lucide-react";
import type { EaExecutionRecord } from "@/data/ea-bridge";

const fieldClass = "w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";

export function OrderControlPanel({
  execution,
  onAction,
}: {
  execution: EaExecutionRecord | null;
  onAction: (message: string) => void;
}) {
  const [volume, setVolume] = useState(execution?.volume ?? 0.05);
  const [sl, setSl] = useState(execution?.sl ?? 2378.25);
  const [tp, setTp] = useState(execution?.tp ?? 2396.25);
  const [partialVolume, setPartialVolume] = useState(0.025);
  const [confirmClose, setConfirmClose] = useState(false);

  const disabled = !execution;
  const submit = (message: string) => {
    onAction(`${message} Preview queued only. No MT5 order was sent.`);
  };

  return (
    <article aria-label="EA order control panel" className="rounded-xl border bg-card shadow-sm">
      <header className="flex items-start gap-3 border-b p-5">
        <span className="rounded-lg bg-primary/10 p-2 text-primary"><ShoppingCart className="h-4 w-4" /></span>
        <div>
          <h2 className="font-semibold">Order control</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">Stage a Buy, Sell, Close, or protection update for the selected MT5 position.</p>
        </div>
      </header>
      <div className="space-y-4 p-5">
        <div className="flex items-center justify-between rounded-lg border bg-muted/30 p-3">
          <div><p className="text-xs font-medium">{execution ? `${execution.symbol} · ${execution.orderId}` : "No open position"}</p><p className="mt-0.5 text-[10px] text-muted-foreground">{execution ? `${execution.volume.toFixed(3)} lots at ${execution.price.toFixed(2)}` : "Connect an EA to enable controls."}</p></div>
          <span className="rounded-full bg-amber-500/10 px-2 py-1 text-[9px] font-semibold text-amber-500">PREVIEW</span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <button type="button" disabled={disabled} onClick={() => submit(`BUY ${volume.toFixed(3)} ${execution?.symbol ?? "XAUUSD"}`)} className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"><Plus className="h-3.5 w-3.5" /> Buy market</button>
          <button type="button" disabled={disabled} onClick={() => submit(`SELL ${volume.toFixed(3)} ${execution?.symbol ?? "XAUUSD"}`)} className="inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 px-3 py-2.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"><Minus className="h-3.5 w-3.5" /> Sell market</button>
        </div>
        <label className="block"><span className="text-xs font-medium">Order volume</span><div className="relative mt-1.5"><input aria-label="Order volume" type="number" min="0.01" step="0.001" value={volume} onChange={(event) => setVolume(Number(event.target.value))} className={`${fieldClass} pr-12`} /><span className="absolute right-3 top-2.5 text-xs text-muted-foreground">lots</span></div></label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block"><span className="text-xs font-medium">Stop loss</span><input aria-label="Stop loss" type="number" step="0.01" value={sl} onChange={(event) => setSl(Number(event.target.value))} className={`${fieldClass} mt-1.5`} /></label>
          <label className="block"><span className="text-xs font-medium">Take profit</span><input aria-label="Take profit" type="number" step="0.01" value={tp} onChange={(event) => setTp(Number(event.target.value))} className={`${fieldClass} mt-1.5`} /></label>
        </div>
        <button type="button" disabled={disabled} onClick={() => submit(`MODIFY protection SL ${sl.toFixed(2)} / TP ${tp.toFixed(2)}`)} className="inline-flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"><Pencil className="h-3.5 w-3.5" /> Modify SL / TP</button>
        <div className="grid gap-3 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 sm:grid-cols-[1fr_auto] sm:items-end">
          <label className="block"><span className="text-xs font-medium">Partial close volume</span><input aria-label="Partial close volume" type="number" min="0.001" step="0.001" value={partialVolume} onChange={(event) => setPartialVolume(Number(event.target.value))} className={`${fieldClass} mt-1.5`} /></label>
          <button type="button" disabled={disabled} onClick={() => submit(`PARTIAL CLOSE ${partialVolume.toFixed(3)} lots`)} className="inline-flex items-center justify-center gap-2 rounded-lg border border-amber-500/40 px-3 py-2 text-xs font-medium text-amber-600 hover:bg-amber-500/10 disabled:cursor-not-allowed disabled:opacity-50"><Minus className="h-3.5 w-3.5" /> Partial close</button>
        </div>
        {confirmClose ? <div role="alertdialog" className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3"><div className="flex gap-2"><AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" /><p className="text-xs text-muted-foreground">Close the full position in the preview queue?</p></div><div className="mt-3 flex gap-2"><button type="button" onClick={() => { submit("CLOSE full position"); setConfirmClose(false); }} className="rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white">Confirm close</button><button type="button" onClick={() => setConfirmClose(false)} className="rounded-lg border px-3 py-2 text-xs">Cancel</button></div></div> : <button type="button" disabled={disabled} onClick={() => setConfirmClose(true)} className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-rose-500/40 px-3 py-2 text-xs font-medium text-rose-600 hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:opacity-50"><CircleX className="h-3.5 w-3.5" /> Close position</button>}
        <p className="flex items-center gap-2 text-[10px] text-muted-foreground"><LockKeyhole className="h-3.5 w-3.5" /> Commands remain page-memory previews until the secure bridge API is connected.</p>
      </div>
    </article>
  );
}
