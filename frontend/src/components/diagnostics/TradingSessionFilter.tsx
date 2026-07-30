export type TradingSessionFilterValue = "ALL" | "ASIA" | "LONDON" | "NEW_YORK";

interface TradingSessionFilterProps {
  value: TradingSessionFilterValue;
  onChange: (value: TradingSessionFilterValue) => void;
  counts: Record<TradingSessionFilterValue, number>;
}

const sessions = [
  { value: "ALL", label: "All sessions", time: "24 hours" },
  { value: "ASIA", label: "Asia", time: "00:00–09:00 UTC" },
  { value: "LONDON", label: "London", time: "08:00–17:00 UTC" },
  { value: "NEW_YORK", label: "New York", time: "13:00–22:00 UTC" },
] as const;

export function TradingSessionFilter({ value, onChange, counts }: TradingSessionFilterProps) {
  return <fieldset><legend className="mb-2 text-xs text-muted-foreground">Trading session</legend><div className="space-y-1.5">{sessions.map((session) => <button key={session.value} type="button" onClick={() => onChange(session.value)} aria-pressed={value === session.value} className={`flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left transition ${value === session.value ? "border-primary bg-primary/10" : "bg-background hover:bg-muted"}`}><span><span className={`block text-xs font-medium ${value === session.value ? "text-primary" : ""}`}>{session.label}</span><span className="text-[10px] text-muted-foreground">{session.time}</span></span><span className="font-mono text-xs text-muted-foreground">{counts[session.value]}</span></button>)}</div></fieldset>;
}