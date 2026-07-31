import os
import sys

p = 'frontend/src/pages/LossPatternAnalysis.tsx'
try:
    with open(p, 'r', encoding='utf-8') as f:
        s = f.read()

    s = s.replace(
        'import { AlertTriangle, ArrowLeft, ArrowUpRight, BrainCircuit, Loader2, ShieldAlert, Target } from "lucide-react";',
        'import { AlertTriangle, ArrowDown, ArrowLeft, ArrowUp, ArrowUpRight, BrainCircuit, Loader2, ShieldAlert, Target } from "lucide-react";'
    )
    s = s.replace(
        'const [loading, setLoading] = useState(true);',
        'const [loading, setLoading] = useState(true);\n  const [comparePeriod, setComparePeriod] = useState("previous_month");'
    )
    s = s.replace(
        'grid grid-cols-3 gap-3',
        'grid grid-cols-4 gap-3'
    )
    s = s.replace(
        '<div><p className="text-[10px] uppercase text-muted-foreground">Confidence</p><p className="mt-1 font-mono text-sm font-semibold">{pattern.confidence}%</p></div>',
        '<div><p className="text-[10px] uppercase text-muted-foreground">Confidence</p><p className="mt-1 font-mono text-sm font-semibold">{pattern.confidence}%</p></div>\n          <div><p className="text-[10px] uppercase text-muted-foreground">Trend</p><p className={`mt-1 flex items-center gap-0.5 font-mono text-sm font-semibold ${pattern.trendDelta > 0 ? "text-rose-500" : pattern.trendDelta < 0 ? "text-emerald-500" : "text-muted-foreground"}`}>{pattern.trendDelta > 0 ? <ArrowUp className="h-3 w-3" /> : pattern.trendDelta < 0 ? <ArrowDown className="h-3 w-3" /> : null}{Math.abs(pattern.trendDelta)}%</p></div>'
    )
    s = s.replace(
        '<p className="mt-1 max-w-2xl text-sm text-muted-foreground">Rank recurring failure conditions before changing strategy parameters.</p>',
        '<p className="mt-1 max-w-2xl text-sm text-muted-foreground">Rank recurring failure conditions before changing strategy parameters. Compare against historical baseline.</p>'
    )
    s = s.replace(
        '<p className="w-fit text-xs text-muted-foreground">Generated {new Date(generatedAt).toLocaleString()}</p>',
        '<div className="flex flex-col items-end gap-2">\n          <select value={comparePeriod} onChange={(e) => setComparePeriod(e.target.value)} className="w-fit rounded-lg border bg-card px-3 py-1.5 text-xs font-medium text-foreground outline-none hover:bg-muted">\n            <option value="previous_month">vs Previous Month</option>\n            <option value="previous_quarter">vs Previous Quarter</option>\n            <option value="baseline">vs Baseline strategy</option>\n          </select>\n          <p className="text-xs text-muted-foreground">Generated {new Date(generatedAt).toLocaleString()}</p>\n        </div>'
    )

    with open(p, 'w', encoding='utf-8') as f:
        f.write(s)
    print("applied")
except Exception as e:
    print(f"Error: {e}")