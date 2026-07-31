import { ArrowLeft, Bell, CheckCircle2, Mail, Monitor, RotateCcw, Save, Smartphone } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";

interface Preferences {
  inApp: boolean;
  email: boolean;
  mobile: boolean;
  criticalPatterns: boolean;
  recommendations: boolean;
  validationResults: boolean;
  sourceHealth: boolean;
  weeklyDigest: boolean;
  quietHours: boolean;
}

const defaults: Preferences = { inApp: true, email: true, mobile: false, criticalPatterns: true, recommendations: true, validationResults: true, sourceHealth: true, weeklyDigest: false, quietHours: true };

export function DiagnosticNotificationSettings() {
  const [preferences, setPreferences] = useState(defaults);
  const [saved, setSaved] = useState(false);
  const [quietStart, setQuietStart] = useState("22:00");
  const [quietEnd, setQuietEnd] = useState("07:00");
  const toggle = (key: keyof Preferences) => { setPreferences((current) => ({ ...current, [key]: !current[key] })); setSaved(false); };
  const reset = () => { setPreferences(defaults); setQuietStart("22:00"); setQuietEnd("07:00"); setSaved(false); };

  return <div className="mx-auto max-w-5xl space-y-6 p-4 sm:p-6 lg:p-8">
    <header><Link to="/diagnostics" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" /> Diagnostic dashboard</Link><div className="mt-4"><div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary"><Bell className="h-4 w-4" /> Alert preferences <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] text-amber-600 dark:text-amber-400">Mock settings</span></div><h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Notification settings</h1><p className="mt-1 text-sm text-muted-foreground">Choose which diagnostic evidence and validation events should get your attention.</p></div></header>

    <SettingsSection title="Delivery channels" detail="Select where diagnostics updates should appear.">
      <Toggle icon={Monitor} title="In-app notifications" detail="Show updates in the notification panel." checked={preferences.inApp} onChange={() => toggle("inApp")} />
      <Toggle icon={Mail} title="Email summaries" detail="Send important evidence updates to the profile email." checked={preferences.email} onChange={() => toggle("email")} />
      <Toggle icon={Smartphone} title="Mobile push" detail="Push urgent controls to a paired mobile device." checked={preferences.mobile} onChange={() => toggle("mobile")} />
    </SettingsSection>

    <SettingsSection title="Diagnostic events" detail="Control which evidence events generate a notification.">
      <Toggle title="Critical loss patterns" detail="A recurring condition crosses the high-severity threshold." checked={preferences.criticalPatterns} onChange={() => toggle("criticalPatterns")} />
      <Toggle title="New recommendations" detail="A corrective control is ready for review or application." checked={preferences.recommendations} onChange={() => toggle("recommendations")} />
      <Toggle title="Validation results" detail="An improvement reaches, misses, or risks its target." checked={preferences.validationResults} onChange={() => toggle("validationResults")} />
      <Toggle title="Data source health" detail="A connector becomes stale, disconnected, or incomplete." checked={preferences.sourceHealth} onChange={() => toggle("sourceHealth")} />
      <Toggle title="Weekly evidence digest" detail="A compact weekly summary of patterns and progress." checked={preferences.weeklyDigest} onChange={() => toggle("weeklyDigest")} />
    </SettingsSection>

    <SettingsSection title="Quiet hours" detail="Mute non-critical notifications during a daily time window.">
      <Toggle title="Enable quiet hours" detail="Critical source failures can still appear in-app." checked={preferences.quietHours} onChange={() => toggle("quietHours")} />
      {preferences.quietHours && <div className="grid gap-3 border-t p-4 sm:grid-cols-2"><label className="text-xs font-medium">Start<input type="time" value={quietStart} onChange={(event) => { setQuietStart(event.target.value); setSaved(false); }} className="mt-1.5 w-full rounded-lg border bg-background px-3 py-2 text-sm" /></label><label className="text-xs font-medium">End<input type="time" value={quietEnd} onChange={(event) => { setQuietEnd(event.target.value); setSaved(false); }} className="mt-1.5 w-full rounded-lg border bg-background px-3 py-2 text-sm" /></label></div>}
    </SettingsSection>

    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4"><div>{saved ? <p className="inline-flex items-center gap-1.5 text-xs text-emerald-500"><CheckCircle2 className="h-4 w-4" /> Mock preferences saved for this session.</p> : <p className="text-xs text-muted-foreground">Settings are not persisted or sent to a backend.</p>}</div><div className="flex gap-2"><button type="button" onClick={reset} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted"><RotateCcw className="h-4 w-4" /> Reset</button><button type="button" onClick={() => setSaved(true)} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground"><Save className="h-4 w-4" /> Save mock settings</button></div></div>
  </div>;
}

function SettingsSection({ title, detail, children }: { title: string; detail: string; children: React.ReactNode }) {
  return <section className="overflow-hidden rounded-xl border bg-card shadow-sm"><div className="border-b p-4"><h2 className="font-semibold">{title}</h2><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div><div className="divide-y">{children}</div></section>;
}

function Toggle({ icon: Icon = Bell, title, detail, checked, onChange }: { icon?: typeof Bell; title: string; detail: string; checked: boolean; onChange: () => void }) {
  return <div className="flex items-center justify-between gap-4 p-4"><div className="flex min-w-0 gap-3"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground"><Icon className="h-4 w-4" /></span><div><h3 className="text-sm font-medium">{title}</h3><p className="mt-0.5 text-xs text-muted-foreground">{detail}</p></div></div><button type="button" role="switch" aria-checked={checked} aria-label={title} onClick={onChange} className={`relative h-6 w-11 shrink-0 rounded-full transition ${checked ? "bg-primary" : "bg-muted"}`}><span className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-1" : "-translate-x-4"}`} /></button></div>;
}