import { Activity, ArrowRight, BarChart3, CheckCircle2, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck, UserRound } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router";
import { startDiagnosticMockSession } from "@/lib/diagnosticAuth";

interface FormState {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

const fieldClass = "w-full rounded-lg border bg-background py-2.5 pl-10 pr-3 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20";

export function DiagnosticAuth() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const registering = pathname === "/register";
  const [form, setForm] = useState<FormState>({ name: "", email: "", password: "", confirmPassword: "" });
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const email = form.email.trim();
    if (registering && form.name.trim().length < 2) {
      setError("Enter a name with at least 2 characters.");
      return;
    }
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError("Enter a valid email address.");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }
    if (registering && form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setSubmitted(true);
    startDiagnosticMockSession();
  };

  const update = (key: keyof FormState, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setError(null);
    setSubmitted(false);
  };

  return <main className="min-h-screen bg-background lg:grid lg:grid-cols-[minmax(0,1.05fr)_minmax(440px,0.95fr)]">
    <section className="relative hidden overflow-hidden border-r bg-slate-950 p-12 text-white lg:flex lg:flex-col lg:justify-between">
      <div aria-hidden="true" className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(59,130,246,0.24),transparent_38%),radial-gradient(circle_at_80%_75%,rgba(16,185,129,0.16),transparent_36%)]" />
      <Link to="/diagnostics" className="relative flex items-center gap-2 text-lg font-semibold"><BarChart3 className="h-6 w-6 text-sky-400" /> Vibe Trade Diagnostics</Link>
      <div className="relative max-w-xl">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-300">Evidence before optimization</p>
        <h1 className="mt-4 text-4xl font-semibold leading-tight">Turn every losing trade into measurable strategy learning.</h1>
        <p className="mt-4 max-w-lg text-sm leading-relaxed text-slate-300">Diagnose recurring failure patterns, prioritize corrective controls, and validate whether each change actually reduces risk.</p>
        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          <Feature icon={Activity} label="Trade diagnostics" />
          <Feature icon={ShieldCheck} label="Evidence controls" />
          <Feature icon={CheckCircle2} label="Progress tracking" />
        </div>
      </div>
      <p className="relative text-xs text-slate-500">XAUUSD production strategy workspace</p>
    </section>

    <section className="flex min-h-screen items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-md">
        <Link to="/diagnostics" className="mb-8 flex items-center gap-2 font-semibold lg:hidden"><BarChart3 className="h-5 w-5 text-primary" /> Vibe Trade Diagnostics</Link>
        <div className="rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><LockKeyhole className="h-5 w-5" /></div>
          <h2 className="mt-5 text-2xl font-semibold tracking-tight">{registering ? "Create your workspace" : "Welcome back"}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{registering ? "Start an evidence-driven diagnostic cycle." : "Continue reviewing your strategy evidence."}</p>
          <span className="mt-3 inline-flex rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400">Mock authentication</span>

          {submitted ? <div className="mt-6 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5 text-center"><CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500" /><h3 className="mt-3 font-semibold">{registering ? "Workspace preview created" : "Mock sign-in successful"}</h3><p className="mt-1 text-xs text-muted-foreground">No account or credential was persisted. Continue to the diagnostics preview.</p><button type="button" onClick={() => { const target = searchParams.get("returnTo"); navigate(target?.startsWith("/") && !target.startsWith("//") ? target : "/diagnostics", { replace: true }); }} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">Open dashboard <ArrowRight className="h-4 w-4" /></button></div> : <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
            {registering && <Field icon={UserRound} label="Full name"><input value={form.name} onChange={(event) => update("name", event.target.value)} autoComplete="name" placeholder="Alex Morgan" className={fieldClass} /></Field>}
            <Field icon={Mail} label="Email address"><input type="email" value={form.email} onChange={(event) => update("email", event.target.value)} autoComplete="email" placeholder="trader@example.com" className={fieldClass} /></Field>
            <Field icon={LockKeyhole} label="Password"><div className="relative"><input type={showPassword ? "text" : "password"} value={form.password} onChange={(event) => update("password", event.target.value)} autoComplete={registering ? "new-password" : "current-password"} placeholder="Minimum 8 characters" className={`${fieldClass} pr-10`} /><button type="button" onClick={() => setShowPassword((current) => !current)} aria-label={showPassword ? "Hide password" : "Show password"} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div></Field>
            {registering && <Field icon={LockKeyhole} label="Confirm password"><input type={showPassword ? "text" : "password"} value={form.confirmPassword} onChange={(event) => update("confirmPassword", event.target.value)} autoComplete="new-password" placeholder="Repeat password" className={fieldClass} /></Field>}
            {!registering && <div className="flex items-center justify-between gap-3 text-xs"><label className="flex cursor-pointer items-center gap-2 text-muted-foreground"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} className="h-4 w-4 accent-primary" /> Remember this device</label><button type="button" className="font-medium text-primary hover:underline">Forgot password?</button></div>}
            {error && <p role="alert" className="rounded-lg bg-rose-500/10 px-3 py-2 text-xs text-rose-500">{error}</p>}
            <button type="submit" className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90">{registering ? "Create mock account" : "Sign in to preview"}<ArrowRight className="h-4 w-4" /></button>
          </form>}
          {!submitted && <p className="mt-6 text-center text-xs text-muted-foreground">{registering ? "Already have an account?" : "New to diagnostics?"} <Link to={registering ? "/login" : "/register"} className="font-medium text-primary hover:underline">{registering ? "Sign in" : "Create account"}</Link></p>}
        </div>
        <p className="mt-4 text-center text-[10px] leading-relaxed text-muted-foreground">Preview only. Do not enter a real password; backend account authentication is not connected yet.</p>
      </div>
    </section>
  </main>;
}

function Field({ icon: Icon, label, children }: { icon: typeof Mail; label: string; children: React.ReactNode }) {
  return <label className="block"><span className="mb-1.5 block text-xs font-medium">{label}</span><div className="relative"><Icon className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-muted-foreground" />{children}</div></label>;
}

function Feature({ icon: Icon, label }: { icon: typeof Activity; label: string }) {
  return <div className="rounded-xl border border-white/10 bg-white/5 p-4"><Icon className="h-5 w-5 text-sky-300" /><p className="mt-3 text-xs font-medium">{label}</p></div>;
}