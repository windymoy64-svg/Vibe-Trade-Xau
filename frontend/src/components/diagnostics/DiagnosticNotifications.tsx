import { Bell, BrainCircuit, Check, CheckCircle2, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { diagnosticNotificationsStub, type DiagnosticNotificationType } from "@/data/diagnostic-notifications";

const iconByType = { PATTERN: BrainCircuit, RECOMMENDATION: Sparkles, VALIDATION: CheckCircle2 } satisfies Record<DiagnosticNotificationType, typeof Bell>;

export function DiagnosticNotifications() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState(diagnosticNotificationsStub);
  const rootRef = useRef<HTMLDivElement>(null);
  const unread = notifications.filter((item) => !item.read).length;

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => { if (!rootRef.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", escape); };
  }, [open]);

  const markRead = (id: string) => setNotifications((current) => current.map((item) => item.id === id ? { ...item, read: true } : item));

  return <div ref={rootRef} className="relative">
    <button type="button" onClick={() => setOpen((current) => !current)} aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`} aria-expanded={open} className="relative rounded-lg border bg-card p-2 text-muted-foreground hover:bg-muted hover:text-foreground"><Bell className="h-4 w-4" />{unread > 0 && <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[9px] font-bold text-white">{unread}</span>}</button>
    {open && <section aria-label="Diagnostic notifications" className="absolute right-0 top-11 z-50 w-[min(380px,calc(100vw-2rem))] rounded-xl border bg-card shadow-xl">
      <div className="flex items-start justify-between gap-3 border-b p-4"><div><h2 className="text-sm font-semibold">Notifications</h2><p className="mt-0.5 text-[10px] text-muted-foreground">Evidence and validation updates</p></div><button type="button" onClick={() => setOpen(false)} aria-label="Close notifications" className="rounded p-1 text-muted-foreground hover:bg-muted"><X className="h-4 w-4" /></button></div>
      <div className="max-h-[420px] overflow-auto">{notifications.length === 0 ? <p className="p-8 text-center text-xs text-muted-foreground">No diagnostic notifications.</p> : notifications.map((item) => { const Icon = iconByType[item.type]; return <article key={item.id} className={`flex gap-3 border-b p-4 last:border-0 ${item.read ? "opacity-65" : "bg-primary/[0.03]"}`}><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"><Icon className="h-4 w-4" /></span><div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-2"><Link to={item.href} onClick={() => { markRead(item.id); setOpen(false); }} className="text-xs font-medium hover:text-primary">{item.title}</Link>{!item.read && <button type="button" onClick={() => markRead(item.id)} aria-label={`Mark ${item.title} as read`} className="shrink-0 rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"><Check className="h-3.5 w-3.5" /></button>}</div><p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">{item.detail}</p><p className="mt-2 text-[9px] text-muted-foreground">{new Date(item.createdAt).toLocaleString()}</p></div></article>; })}</div>
      <div className="flex items-center justify-between border-t p-3"><span className="text-[10px] text-muted-foreground">Preview notifications</span><button type="button" disabled={unread === 0} onClick={() => setNotifications((current) => current.map((item) => ({ ...item, read: true })))} className="text-[10px] font-medium text-primary disabled:opacity-50">Mark all as read</button></div>
    </section>}
  </div>;
}