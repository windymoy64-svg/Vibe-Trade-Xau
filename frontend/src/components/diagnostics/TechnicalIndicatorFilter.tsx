interface TechnicalIndicatorFilterProps {
  ema: string;
  onEmaChange: (value: string) => void;
  minRsi: number;
  maxRsi: number;
  onRsiChange: (min: number, max: number) => void;
  minAtr: number;
  onAtrChange: (value: number) => void;
}

const clampRsi = (value: number) => Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));

export function TechnicalIndicatorFilter({ ema, onEmaChange, minRsi, maxRsi, onRsiChange, minAtr, onAtrChange }: TechnicalIndicatorFilterProps) {
  return <fieldset className="space-y-3"><legend className="mb-2 text-xs text-muted-foreground">Technical indicators</legend><label className="block"><span className="mb-1.5 block text-xs text-muted-foreground">EMA alignment</span><select value={ema} onChange={(event) => onEmaChange(event.target.value)} className="w-full rounded-lg border bg-background px-3 py-2 text-sm"><option value="ALL">All alignments</option><option value="BULLISH">Bullish</option><option value="BEARISH">Bearish</option><option value="MIXED">Mixed</option></select></label><label className="block"><span className="mb-1.5 flex justify-between text-xs text-muted-foreground"><span>RSI range</span><span>{minRsi}–{maxRsi}</span></span><div className="grid grid-cols-2 gap-2"><input aria-label="Minimum RSI" type="number" min="0" max="100" value={minRsi} onChange={(event) => onRsiChange(Math.min(clampRsi(Number(event.target.value)), maxRsi), maxRsi)} className="w-full rounded-lg border bg-background px-3 py-2 text-sm" /><input aria-label="Maximum RSI" type="number" min="0" max="100" value={maxRsi} onChange={(event) => onRsiChange(minRsi, Math.max(clampRsi(Number(event.target.value)), minRsi))} className="w-full rounded-lg border bg-background px-3 py-2 text-sm" /></div></label><label className="block"><span className="mb-1.5 flex justify-between text-xs text-muted-foreground"><span>Minimum ATR</span><span>≥ {minAtr.toFixed(1)}</span></span><input type="range" min="0" max="8" step="0.1" value={minAtr} onChange={(event) => onAtrChange(Number(event.target.value))} className="w-full accent-[hsl(var(--primary))]" /></label></fieldset>;
}