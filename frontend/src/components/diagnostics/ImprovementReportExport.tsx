import { Download, FileText, X } from "lucide-react";
import { useEffect, useState } from "react";
import type { ImprovementActivity, ImprovementTimelineEvent, LossReductionPoint, SuccessMetric } from "@/data/diagnostic-improvements";

interface Props {
  timeline: ImprovementTimelineEvent[];
  lossReduction: LossReductionPoint[];
  metrics: SuccessMetric[];
  activities: ImprovementActivity[];
}

function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[character] ?? character);
}

export function ImprovementReportExport({ timeline, lossReduction, metrics, activities }: Props) {
  const [open, setOpen] = useState(false);
  const [sections, setSections] = useState({ metrics: true, timeline: true, activity: true });
  useEffect(() => { if (!open) return; const close = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); }; window.addEventListener("keydown", close); return () => window.removeEventListener("keydown", close); }, [open]);

  const exportReport = () => {
    const popup = window.open("", "_blank", "noopener,noreferrer");
    if (!popup) return;
    const firstRate = lossReduction[0]?.lossRate ?? 0;
    const lastRate = lossReduction[lossReduction.length - 1]?.lossRate ?? 0;
    const metricRows = metrics.map((item) => `<tr><td>${escapeHtml(item.label)}</td><td>${escapeHtml(item.current)}</td><td>${escapeHtml(item.target)}</td><td>${escapeHtml(item.status)}</td></tr>`).join("");
    const timelineRows = timeline.map((item) => `<tr><td>${escapeHtml(new Date(item.occurredAt).toLocaleString())}</td><td>${escapeHtml(item.title)}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(item.owner)}</td></tr>`).join("");
    const activityRows = activities.map((item) => `<li><strong>${escapeHtml(item.actor)}</strong> — ${escapeHtml(item.message)} <small>${escapeHtml(new Date(item.occurredAt).toLocaleString())}</small></li>`).join("");
    popup.document.write(`<html><head><title>Improvement progress report</title><style>body{font:14px Arial;padding:32px;color:#111}h1{margin-bottom:4px}.meta{color:#555}.summary{display:flex;gap:12px;margin:20px 0}.metric{border:1px solid #ddd;border-radius:8px;padding:12px;min-width:150px}.metric strong{display:block;font-size:22px;margin-top:5px}table{width:100%;border-collapse:collapse;margin:12px 0 24px}th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f3f4f6}li{margin:8px 0}small{display:block;color:#666;margin-top:2px}button{padding:10px 14px}@media print{button{display:none}}</style></head><body><h1>Improvement progress report</h1><p class="meta">Generated ${escapeHtml(new Date().toLocaleString())}</p><div class="summary"><div class="metric">Baseline loss rate<strong>${firstRate}%</strong></div><div class="metric">Latest loss rate<strong>${lastRate}%</strong></div><div class="metric">Tracked changes<strong>${timeline.length}</strong></div></div>${sections.metrics ? `<h2>Success metrics</h2><table><thead><tr><th>Metric</th><th>Current</th><th>Target</th><th>Status</th></tr></thead><tbody>${metricRows}</tbody></table>` : ""}${sections.timeline ? `<h2>Improvement timeline</h2><table><thead><tr><th>Date</th><th>Change</th><th>Status</th><th>Owner</th></tr></thead><tbody>${timelineRows}</tbody></table>` : ""}${sections.activity ? `<h2>Activity log</h2><ul>${activityRows}</ul>` : ""}<button onclick="window.print()">Save as PDF / Print</button></body></html>`);
    popup.document.close();
    setOpen(false);
  };

  const selectedCount = Object.values(sections).filter(Boolean).length;
  return <>
    <button type="button" onClick={() => setOpen(true)} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90"><Download className="h-4 w-4" /> Export report</button>
    {open && <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
      <div role="dialog" aria-modal="true" aria-labelledby="export-report-title" className="w-full max-w-md rounded-xl border bg-card p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3"><div className="flex gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary"><FileText className="h-4 w-4" /></span><div><h2 id="export-report-title" className="font-semibold">Export improvement report</h2><p className="mt-1 text-xs text-muted-foreground">Choose sections for a print-friendly PDF report.</p></div></div><button type="button" onClick={() => setOpen(false)} aria-label="Close export dialog" className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"><X className="h-4 w-4" /></button></div>
        <fieldset className="mt-5 space-y-2"><legend className="mb-2 text-xs font-medium">Report sections</legend>{([['metrics', 'Success metrics'], ['timeline', 'Improvement timeline'], ['activity', 'Activity log']] as const).map(([key, label]) => <label key={key} className="flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm hover:bg-muted/50"><input type="checkbox" checked={sections[key]} onChange={(event) => setSections((current) => ({ ...current, [key]: event.target.checked }))} className="h-4 w-4 accent-primary" />{label}</label>)}</fieldset>
        {selectedCount === 0 && <p className="mt-3 text-xs text-amber-500">Select at least one report section.</p>}
        <div className="mt-5 flex justify-end gap-2"><button type="button" onClick={() => setOpen(false)} className="rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted">Cancel</button><button type="button" disabled={selectedCount === 0} onClick={exportReport} className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"><Download className="h-4 w-4" /> Open report</button></div>
      </div>
    </div>}
  </>;
}