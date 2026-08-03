import { useEffect, useState } from "react";
import { Clock3, Radio, X } from "lucide-react";
import type { EaPendingOrderRecord } from "@/data/ea-bridge";

const statusTone: Record<EaPendingOrderRecord["status"], string> = {
  PLACED: "bg-sky-500/10 text-sky-500",
  TRIGGER_NEAR: "bg-amber-500/10 text-amber-500",
  CANCEL_REQUESTED: "bg-rose-500/10 text-rose-500",
};

export function LivePendingOrders({ initial, onAction }: { initial: EaPendingOrderRecord[]; onAction: (message: string) => void }) {
  const [orders, setOrders] = useState(initial);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setOrders((current) => current.map((order, index) => ({ ...order, currentPrice: order.currentPrice + (index % 2 === 0 ? 0.02 : -0.01) })));
    }, 1_000);
    return () => window.clearInterval(timer);
  }, []);

  const cancel = (id: string) => {
    const target = orders.find((order) => order.id === id);
    if (!target) return;
    setOrders((current) => current.map((order) => order.id === id ? { ...order, status: "CANCEL_REQUESTED" as const } : order));
    onAction(`CANCEL ${target.ticket} requested. Preview only; pending order remains active in MT5.`);
  };

  return (
    <article aria-label="Live pending MT5 orders" className="rounded-xl border bg-card shadow-sm">
      <header className="flex items-start justify-between gap-3 border-b p-5"><div className="flex items-start gap-3"><span className="rounded-lg bg-primary/10 p-2 text-primary"><Clock3 className="h-4 w-4" /></span><div><h2 className="font-semibold">Pending MT5 orders</h2><p className="mt-0.5 text-xs text-muted-foreground">Live orders waiting for the XAUUSD trigger price.</p></div></div><span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-1 text-[9px] font-semibold text-emerald-500"><Radio className="h-3 w-3" /> LIVE</span></header>
      {orders.length === 0 ? <p className="p-5 text-xs text-muted-foreground">No pending orders.</p> : <div className="divide-y">{orders.map((order) => {
        const distance = Math.abs(order.currentPrice - order.targetPrice);
        return <div key={order.id} className="grid gap-3 p-5 sm:grid-cols-[1.2fr_repeat(3,minmax(90px,0.7fr))_auto] sm:items-center"><div><div className="flex flex-wrap items-center gap-2"><p className={`font-mono text-xs font-semibold ${order.type.startsWith("BUY") ? "text-emerald-500" : "text-rose-500"}`}>{order.type.replace("_", " ")}</p><span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${statusTone[order.status]}`}>{order.status}</span></div><p className="mt-1 font-mono text-[10px] text-muted-foreground">{order.ticket} · {order.terminal}</p></div><Meta label="Target / market" value={`${order.targetPrice.toFixed(2)} / ${order.currentPrice.toFixed(2)}`} /><Meta label="Distance" value={`${distance.toFixed(2)} USD`} /><Meta label="SL / TP" value={`${order.sl.toFixed(2)} / ${order.tp.toFixed(2)}`} /><button type="button" disabled={order.status === "CANCEL_REQUESTED"} onClick={() => cancel(order.id)} className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-2 text-xs text-rose-500 hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:opacity-50"><X className="h-3.5 w-3.5" /> Cancel</button></div>;
      })}</div>}
    </article>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div><p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 font-mono text-xs">{value}</p></div>;
}
