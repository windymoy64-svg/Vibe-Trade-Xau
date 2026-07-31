import { ArrowLeft, CalendarDays, CheckCircle2, Clock3, Mail, RotateCcw, Save, ShieldCheck, UserRound } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { diagnosticProfileStub, type DiagnosticProfile } from "@/data/diagnostic-profile";

const fieldClass = "w-full rounded-lg border bg-background px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";

export function DiagnosticProfileSettings() {
  const [profile, setProfile] = useState<DiagnosticProfile>(diagnosticProfileStub);
  const [saved, setSaved] = useState(false);
  const initials = profile.name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "VT";

  const update = (key: keyof DiagnosticProfile, value: string) => {
    setProfile((current) => ({ ...current, [key]: value }));
    setSaved(false);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setSaved(true);
  };
  const reset = () => {
    setProfile(diagnosticProfileStub);
    setSaved(false);
  };

  return <div className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header>
      <Link to="/diagnostics" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Diagnostic dashboard</Link>
      <div className="mt-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end"><div><div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><UserRound className="h-4 w-4" /> Account preferences <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">Preview data</span></div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Profile settings</h1><p className="mt-1 text-sm text-muted-foreground">Manage the identity and trading context shown across diagnostics reports.</p></div><Link to="/settings" className="text-xs font-medium text-primary hover:underline">Open technical settings</Link></div>
    </header>

    <section className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="h-fit rounded-xl border bg-card p-5 text-center shadow-sm">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-primary/10 text-2xl font-semibold text-primary">{initials}</div>
        <h2 className="mt-4 font-semibold">{profile.name || "Unnamed trader"}</h2><p className="mt-1 text-xs text-muted-foreground">{profile.role}</p>
        <span className="mt-3 inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-1 text-[10px] font-medium text-emerald-500"><ShieldCheck className="h-3 w-3" /> Preview account</span>
        <dl className="mt-5 space-y-3 border-t pt-4 text-left text-xs"><div><dt className="flex items-center gap-1.5 text-muted-foreground"><CalendarDays className="h-3.5 w-3.5" /> Joined</dt><dd className="mt-1 font-medium">{new Date(profile.joinedAt).toLocaleDateString()}</dd></div><div><dt className="flex items-center gap-1.5 text-muted-foreground"><Clock3 className="h-3.5 w-3.5" /> Last active</dt><dd className="mt-1 font-medium">{new Date(profile.lastActiveAt).toLocaleString()}</dd></div><div><dt className="flex items-center gap-1.5 text-muted-foreground"><Mail className="h-3.5 w-3.5" /> Account ID</dt><dd className="mt-1 break-all font-mono text-[10px]">{profile.id}</dd></div></dl>
      </aside>

      <form onSubmit={submit} className="rounded-xl border bg-card shadow-sm">
        <div className="border-b p-5"><h2 className="font-semibold">Personal information</h2><p className="mt-1 text-xs text-muted-foreground">Mock changes remain in this browser session only.</p></div>
        <div className="grid gap-5 p-5 sm:grid-cols-2">
          <Field label="Full name"><input value={profile.name} onChange={(event) => update("name", event.target.value)} className={fieldClass} required minLength={2} /></Field>
          <Field label="Email address"><input type="email" value={profile.email} onChange={(event) => update("email", event.target.value)} className={fieldClass} required /></Field>
          <Field label="Role"><input value={profile.role} onChange={(event) => update("role", event.target.value)} className={fieldClass} /></Field>
          <Field label="Timezone"><select value={profile.timezone} onChange={(event) => update("timezone", event.target.value)} className={fieldClass}><option>Asia/Jakarta</option><option>Asia/Singapore</option><option>Europe/London</option><option>America/New_York</option><option>UTC</option></select></Field>
          <Field label="Trading focus"><select value={profile.tradingFocus} onChange={(event) => update("tradingFocus", event.target.value)} className={fieldClass}><option>XAUUSD intraday</option><option>XAUUSD swing</option><option>Multi-pair forex</option><option>Research only</option></select></Field>
          <div className="sm:col-span-2"><Field label="Profile note"><textarea rows={4} maxLength={240} value={profile.bio} onChange={(event) => update("bio", event.target.value)} className={fieldClass} /><span className="mt-1 block text-right text-[10px] text-muted-foreground">{profile.bio.length}/240</span></Field></div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t p-5"><div>{saved && <p className="inline-flex items-center gap-1.5 text-xs text-emerald-500"><CheckCircle2 className="h-4 w-4" /> Mock profile saved for this session.</p>}</div><div className="flex gap-2"><button type="button" onClick={reset} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted"><RotateCcw className="h-4 w-4" /> Reset</button><button type="submit" className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground"><Save className="h-4 w-4" /> Save mock profile</button></div></div>
      </form>
    </section>
  </div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span>{children}</label>;
}