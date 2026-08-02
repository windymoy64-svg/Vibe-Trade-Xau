import { useRef, useState, type DragEvent } from "react";
import { CheckCircle2, FileJson, FileSpreadsheet, RotateCcw, UploadCloud } from "lucide-react";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const supportedExtensions = ["csv", "json"];

export function OhlcFileUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const validateFile = (file?: File) => {
    if (!file) return;
    const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!supportedExtensions.includes(extension)) {
      setSelectedFile(null);
      setError("Unsupported format. Choose a CSV or JSON file.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null);
      setError("File exceeds the 5 MiB preview limit.");
      return;
    }
    setSelectedFile(file);
    setError(null);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragActive(false);
    validateFile(event.dataTransfer.files[0]);
  };
  const reset = () => {
    setSelectedFile(null);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return <div className="border-t p-5">
    <input ref={inputRef} id="precision-ohlc-file" type="file" accept=".csv,.json,text/csv,application/json" onChange={(event) => validateFile(event.target.files?.[0])} className="sr-only" />
    {!selectedFile ? <div onDragEnter={(event) => { event.preventDefault(); setDragActive(true); }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragActive(false)} onDrop={handleDrop} className={`rounded-xl border border-dashed p-5 text-center transition ${dragActive ? "border-primary bg-primary/5" : "bg-muted/20"}`}><UploadCloud className="mx-auto h-7 w-7 text-primary" /><p className="mt-2 text-sm font-medium">Drop OHLCV data here</p><p className="mt-1 text-xs text-muted-foreground">CSV or JSON · maximum 5 MiB · processed in page memory</p><button type="button" onClick={() => inputRef.current?.click()} className="mt-3 rounded-lg border bg-background px-3 py-2 text-xs font-medium hover:bg-muted">Choose file</button></div> : <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4"><div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div className="flex min-w-0 items-center gap-3"><span className="rounded-lg bg-emerald-500/10 p-2 text-emerald-500">{selectedFile.name.toLowerCase().endsWith(".json") ? <FileJson className="h-5 w-5" /> : <FileSpreadsheet className="h-5 w-5" />}</span><div className="min-w-0"><p className="truncate text-sm font-medium">{selectedFile.name}</p><p className="mt-0.5 text-xs text-muted-foreground">{formatBytes(selectedFile.size)} · {selectedFile.name.split(".").pop()?.toUpperCase()} · ready for preview parsing</p></div></div><div className="flex items-center gap-2"><span className="flex items-center gap-1 text-xs text-emerald-500"><CheckCircle2 className="h-4 w-4" /> Ready</span><button type="button" aria-label="Remove selected file" onClick={reset} className="rounded-lg border p-2 text-muted-foreground hover:bg-muted hover:text-foreground"><RotateCcw className="h-3.5 w-3.5" /></button></div></div></div>}
    {error && <p role="alert" className="mt-2 text-xs text-rose-500">{error}</p>}
    <p className="mt-2 text-[10px] text-muted-foreground">No file content is uploaded or persisted by this frontend preview.</p>
  </div>;
}

function formatBytes(bytes: number): string { if (bytes < 1024) return `${bytes} B`; if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`; return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`; }