import { useState } from "react";
import { Download, FileCode, BookOpen, Terminal, CheckCircle2, Info } from "lucide-react";

type StepNumber = 1 | 2 | 3 | 4;

interface GuideStep {
  number: StepNumber;
  title: string;
  description: string;
  command?: string;
  screenshot?: string;
}

const steps: GuideStep[] = [
  {
    number: 1,
    title: "Access the EA Repository",
    description: "Navigate to your Vibe Trade repository or download center to locate the Expert Advisor files.",
  },
  {
    number: 2,
    title: "Download Compiled .ex5 File",
    description: "Get the latest compiled version of the EA. Ensure you have the matching source files for customization.",
    command: "wget https://github.com/windymoy64-svg/Vibe-Trade-Xau/releases/download/v1.2.3/vibe-trade-ea-v1.2.3.ex5",
  },
  {
    number: 3,
    title: "Copy to MT5 Data Folder",
    description: "Place the downloaded file in the correct MQL5 directory for your MT5 terminal.",
    command: "cp vibe-trade-ea-v1.2.3.ex5 \"~/AppData/Roaming/MetaQuotes/Terminal/[INSTANCE_ID]/MQL5/Experts/\"",
  },
  {
    number: 4,
    title: "Compile and Attach",
    description: "Open MetaEditor, compile if needed, then attach the EA to your XAUUSD chart with desired parameters.",
  },
];

export function EaDownloadGuide() {
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="space-y-4">
      <h3 className="font-semibold flex items-center gap-2">
        <BookOpen className="h-5 w-5 text-primary" />
        Download & Install Guide
      </h3>
      <p className="text-xs text-muted-foreground">Follow these steps to deploy the Vibe Trade EA to MT5</p>

      <div className="rounded-lg border bg-card">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-between px-4 py-3 text-start hover:bg-muted/50"
        >
          <span className="text-sm font-medium">Installation Steps</span>
          {expanded ? "▼" : "▶"}
        </button>

        {expanded && (
          <div className="border-t p-4">
            <ol className="space-y-4">
              {steps.map((step) => (
                <li key={step.number} className="relative pl-6">
                  <div
                    onClick={() => setActiveStep(activeStep === step.number ? null : step.number)}
                    className={`absolute -left-3 cursor-pointer rounded-full border-2 bg-card ${
                      activeStep === step.number
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-muted hover:border-primary"
                    } flex h-6 w-6 items-center justify-center text-xs font-bold`}
                  >
                    {step.number}
                  </div>

                  <div className="rounded-lg border bg-card/50 p-3">
                    <p className="font-medium text-sm">{step.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{step.description}</p>

                    {step.command && (
                      <div className="mt-2 overflow-hidden rounded-md bg-slate-900 p-3">
                        <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-400">
                          <Terminal className="h-3 w-3" />
                          Command
                        </div>
                        <pre className="overflow-x-auto text-xs font-mono text-emerald-400 whitespace-pre-wrap break-all">
                          {step.command}
                        </pre>
                      </div>
                    )}

                    <div className="mt-2 flex items-center gap-2 text-[10px] text-muted-foreground">
                      <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                      <span>{step.number}. {step.title.split(" ")[0]}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      <div className="rounded-lg border bg-amber-500/5 p-4">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-amber-500 mt-0.5" />
          <div className="text-xs text-amber-700">
            <p className="font-medium">Prerequisites</p>
            <ul className="mt-1 list-disc space-y-1 pl-4">
              <li>Active MetaTrader 5 account (real or demo)</li>
              <li>MetaEditor installed (included with MT5)</li>
              <li>MCP access token for secure connectivity</li>
              <li>Stable internet connection for token validation</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="rounded-lg border bg-card p-4">
        <h4 className="font-medium text-sm">Quick Links</h4>
        <div className="mt-2 space-y-2">
          <button className="flex w-full items-center gap-2 rounded-md border bg-card px-3 py-2 text-left text-xs font-medium hover:bg-muted">
            <FileCode className="h-3.5 w-3.5" />
            View Source Code
          </button>
          <button className="flex w-full items-center gap-2 rounded-md border bg-card px-3 py-2 text-left text-xs font-medium hover:bg-muted">
            <Download className="h-3.5 w-3.5" />
            Download Latest Release
          </button>
          <button className="flex w-full items-center gap-2 rounded-md border bg-card px-3 py-2 text-left text-xs font-medium hover:bg-muted">
            <BookOpen className="h-3.5 w-3.5" />
            Documentation
          </button>
        </div>
      </div>
    </div>
  );
}
