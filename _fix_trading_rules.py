from pathlib import Path

p = Path("frontend/src/pages/AutoTrade.tsx")
s = p.read_text(encoding="utf-8")

# Semua penggantian yang diperlukan di section TRADING RULES
fixes = [
    ('value={lotSize} onChange={setLotSize}',           'value={values.lotSize} onChange={setters.setLotSize}'),
    ('value={stopLoss} onChange={setStopLoss}',         'value={values.stopLoss} onChange={setters.setStopLoss}'),
    ('value={takeProfit} onChange={setTakeProfit}',     'value={values.takeProfit} onChange={setters.setTakeProfit}'),
    ('value={risk} onChange={setRisk}',                 'value={values.risk} onChange={setters.setRisk}'),
    ('value={dailyLoss} onChange={setDailyLoss}',       'value={values.dailyLoss} onChange={setters.setDailyLoss}'),
    ('checked={paperMode} onChange={(event) => setPaperMode(event.target.checked)}',
     'checked={values.paperMode} onChange={(event) => setters.setPaperMode(event.target.checked)}'),
]

for old, new in fixes:
    if old in s:
        s = s.replace(old, new)
        print(f"OK: {old[:40]}")
    else:
        print(f"MISS: {old[:40]}")

p.write_text(s, encoding="utf-8")
print("DONE")
from pathlib import Path

p = Path("frontend/src/pages/AutoTrade.tsx")
s = p.read_text(encoding="utf-8")

# Fix 1: NumField harus pakai values/setters dari SettingsModal scope
old_numfield = """function NumField({ label, value, onChange, min, max, step }: { label: string; value: number; onChange: (v: number) => void; min: number; max: number; step: number }) {
  const decimals = step < 1 ? (step.toString().split(".")[1] || "").length : 0;
  return (
    <label className="text-[10px] text-slate-500">{label}
      <div className="mt-1 flex items-center gap-1">
        <button type="button" onClick={() => { const next = Number((value - step).toFixed(decimals)); onChange(Math.max(min, next)); }} className="terminal-button bg-slate-700 text-slate-200 h-7 w-7 text-xs font-bold">−</button>
        <input type="number" min={min} max={max} step={step} value={value} onChange={(e) => { const n = Number(e.target.value); if (!isNaN(n) && n >= min && n <= max) onChange(Number(n.toFixed(decimals))); }} className="terminal-input flex-1 text-center" />
        <button type="button" onClick={() => { const next = Number((value + step).toFixed(decimals)); onChange(Math.min(max, next)); }} className="terminal-button bg-slate-700 text-slate-200 h-7 w-7 text-xs font-bold">+</button>
      </div>
    </label>
  );
}"""

new_numfield = """function NumField({ label, value, onChange, min, max, step }: { label: string; value: number; onChange: (v: number) => void; min: number; max: number; step: number }) {
  const decimals = step < 1 ? (step.toString().split(".")[1] || "").length : 0;
  return (
    <label className="text-[10px] text-slate-500">{label}
      <div className="mt-1 flex items-center gap-1">
        <button type="button" onClick={() => { const next = Number((value - step).toFixed(decimals)); onChange(Math.max(min, next)); }} className="terminal-button bg-slate-700 text-slate-200 h-7 w-7 text-xs font-bold">−</button>
        <input type="number" min={min} max={max} step={step} value={value} onChange={(e) => { const n = Number(e.target.value); if (!isNaN(n) && n >= min && n <= max) onChange(Number(n.toFixed(decimals))); }} className="terminal-input flex-1 text-center" />
        <button type="button" onClick={() => { const next = Number((value + step).toFixed(decimals)); onChange(Math.min(max, next)); }} className="terminal-button bg-slate-700 text-slate-200 h-7 w-7 text-xs font-bold">+</button>
      </div>
    </label>
  );
}"""

s = s.replace(old_numfield, new_numfield)

# Fix 2: Ganti hardcoded lotSize/setLotSize dengan values.xxx / setters.setxxx
replacements = [
    ('value={lotSize} onChange={setLotSize}', 'value={values.lotSize} onChange={setters.setLotSize}'),
    ('value={stopLoss} onChange={setStopLoss}', 'value={values.stopLoss} onChange={setters.setStopLoss}'),
    ('value={takeProfit} onChange={setTakeProfit}', 'value={values.takeProfit} onChange={setters.setTakeProfit}'),
    ('value={risk} onChange={setRisk}', 'value={values.risk} onChange={setters.setRisk}'),
    ('value={dailyLoss} onChange={setDailyLoss}', 'value={values.dailyLoss} onChange={setters.setDailyLoss}'),
    ('checked={paperMode} onChange={(event) => setPaperMode(event.target.checked)}', 'checked={values.paperMode} onChange={(event) => setters.setPaperMode(event.target.checked)}'),
]
for old, new in replacements:
    s = s.replace(old, new)

# Fix 3: Hapus unused fields dan setterMap declarations
s = s.replace('  const fields: Array<[string, keyof Omit<ModalValues, "paperMode">, number, number, number]> = [["Lot size", "lotSize", 0.01, 1, 0.01], ["Stop Loss (pips)", "stopLoss", 5, 250, 1], ["Take Profit (pips)", "takeProfit", 10, 500, 1], ["Risk / trade (%)", "risk", 0.01, 5, 0.01], ["Daily loss limit (%)", "dailyLoss", 0.1, 20, 0.1]];\n  const setterMap = { lotSize: setters.setLotSize, stopLoss: setters.setStopLoss, takeProfit: setters.setTakeProfit, risk: setters.setRisk, dailyLoss: setters.setDailyLoss };\n', '')

p.write_text(s, encoding="utf-8")
print("FIXED OK")
from pathlib import Path

p = Path("frontend/src/pages/AutoTrade.tsx")
s = p.read_text(encoding="utf-8")

# Find the TRADING RULES section
marker = "TRADING RULES"
idx = s.find(marker)
if idx == -1:
    print("MARKER NOT FOUND")
    raise SystemExit(1)

# Walk backwards to find the <section> opening tag
start = s.rfind("<section>", 0, idx)
# Walk forward to find matching </section>
end = s.find("</section>", idx)
end += len("</section>")

old = s[start:end]

# New hardcoded JSX — no more fields.map / setterMap / values[key]
new_section = """<section><h3 className="terminal-title mt-5">3 \u00b7 TRADING RULES</h3><div className="mt-3 grid grid-cols-2 gap-3">
          <NumField label="Lot size" value={lotSize} onChange={setLotSize} min={0.01} max={1} step={0.01} />
          <NumField label="Stop Loss (pips)" value={stopLoss} onChange={setStopLoss} min={5} max={250} step={1} />
          <NumField label="Take Profit (pips)" value={takeProfit} onChange={setTakeProfit} min={10} max={500} step={1} />
          <NumField label="Risk / trade (%)" value={risk} onChange={setRisk} min={0.01} max={5} step={0.01} />
          <NumField label="Daily loss limit (%)" value={dailyLoss} onChange={setDailyLoss} min={0.1} max={20} step={0.1} />
        </div><label className="mt-4 flex items-center gap-2 text-xs"><input type="checkbox" checked={paperMode} onChange={(event) => setPaperMode(event.target.checked)} /> Paper mode (disarankan)</label></section>"""

s = s[:start] + new_section + s[end:]

# Also add the NumField component before the SettingsModal function
# Find where to insert it — before "function SettingsModal"
if "function NumField" not in s:
    insert_marker = "function SettingsModal"
    ins = s.find(insert_marker)
    numfield_def = """function NumField({ label, value, onChange, min, max, step }: { label: string; value: number; onChange: (v: number) => void; min: number; max: number; step: number }) {
  const decimals = step < 1 ? (step.toString().split(".")[1] || "").length : 0;
  return (
    <label className="text-[10px] text-slate-500">{label}
      <div className="mt-1 flex items-center gap-1">
        <button type="button" onClick={() => { const next = Number((value - step).toFixed(decimals)); onChange(Math.max(min, next)); }} className="terminal-button bg-slate-700 text-slate-200 h-7 w-7 text-xs font-bold">−</button>
        <input type="number" min={min} max={max} step={step} value={value} onChange={(e) => { const n = Number(e.target.value); if (!isNaN(n) && n >= min && n <= max) onChange(Number(n.toFixed(decimals))); }} className="terminal-input flex-1 text-center" />
        <button type="button" onClick={() => { const next = Number((value + step).toFixed(decimals)); onChange(Math.min(max, next)); }} className="terminal-button bg-slate-700 text-slate-200 h-7 w-7 text-xs font-bold">+</button>
      </div>
    </label>
  );
}

"""
    s = s[:ins] + numfield_def + s[ins:]

p.write_text(s, encoding="utf-8")
print("PATCHED OK")
