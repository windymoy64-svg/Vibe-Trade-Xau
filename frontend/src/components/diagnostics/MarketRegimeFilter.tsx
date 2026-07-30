import { Activity, Radio, TrendingUp, Zap } from "lucide-react";

export type MarketRegimeFilterValue = "ALL" | "TRENDING" | "RANGING" | "BREAKOUT";

interface MarketRegimeFilterProps {
  value: MarketRegimeFilterValue;
  onChange: (value: MarketRegimeFilterValue) => void;
  counts: Record<MarketRegimeFilterValue, number>;
}

const regimes = [
  { value: "ALL", label: "All", icon: Radio },
  { value: "TRENDING", label: "Trending", icon: TrendingUp },
  { value: "RANGING", label: "Ranging", icon: Activity },
  { value: "BREAKOUT", label: "Breakout", icon: Zap },
] as const;

export function MarketRegimeFilter({ value, onChange, counts }: MarketRegimeFilterProps) {
  return <fieldset><legend className="mb-2 text-xs text-muted-foreground">Market regime</legend><div className="grid grid-cols-2 gap-2">{regimes.map(({ value: option, label, icon: Icon }) => <button key={option} type="button" aria-pressed={value === option} onClick={() => onChange(option)} className={`rounded-lg border p-2.5 text-left transition ${value === option ? "border-primary bg-primary/10 text-primary" : "bg-background hover:bg-muted"}`}><div className="flex items-center justify-between"><Icon className="h-3.5 w-3.5" /><span className="font-mono text-[10px]">{counts[option]}</span></div><div className="mt-1.5 text-xs font-medium">{label}</div></button>)}</div></fieldset>;
}