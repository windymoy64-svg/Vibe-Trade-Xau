import { useState } from "react";
import { Bot, Users, ToggleLeft, ToggleRight } from "lucide-react";

type ExecutionMode = "MANUAL" | "AUTO_BY_AI";

interface ModeSetting {
  id: string;
  name: string;
  description: string;
  mode: ExecutionMode;
  isActive: boolean;
  settings?: {
    maxLotSize?: number;
    minLotSize?: number;
    riskPerTrade?: number;
    enabledIndicators?: string[];
  };
}

const defaultSettings: ModeSetting[] = [
  {
    id: "m1",
    name: "Manual Trading",
    description: "Execute trades manually with full control over entry and exit points",
    mode: "MANUAL",
    isActive: true,
    settings: {
      maxLotSize: 2.0,
      minLotSize: 0.01,
      enabledIndicators: ["Price Action", "Support/Resistance", "Volume"],
    },
  },
  {
    id: "m2",
    name: "AI Automated",
    description: "Let the AI system generate and execute trades based on market signals",
    mode: "AUTO_BY_AI",
    isActive: false,
    settings: {
      maxLotSize: 0.3,
      minLotSize: 0.01,
      riskPerTrade: 1.0,
      enabledIndicators: ["EMA Cross", "RSI", "ATR", "MACD", "Bollinger Bands"],
    },
  },
];

export function ExecutionModeToggle() {
  const [settings, setSettings] = useState<ModeSetting[]>(defaultSettings);
  const [selectedMode, setSelectedMode] = useState<ExecutionMode>("MANUAL");

  const toggleMode = (modeId: string) => {
    setSettings((prev) =>
      prev.map((s) => ({
        ...s,
        isActive: s.id === modeId ? !s.isActive : false,
      }))
    );
  };

  const activeSetting = settings.find((s) => s.isActive) || settings[0];

  return (
    <div className="space-y-4">
      <h3 className="font-semibold flex items-center gap-2">
        <ToggleLeft className="h-5 w-5 text-primary" />
        Execution Mode Control
      </h3>
      <p className="text-xs text-muted-foreground">Switch between manual trading and AI automated execution</p>

      <div className="rounded-xl border bg-card p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          {/* Manual Mode Card */}
          <div
            className={`flex-1 cursor-pointer rounded-lg border-2 p-4 transition-all ${
              selectedMode === "MANUAL"
                ? "border-sky-500 bg-sky-500/5"
                : "border-muted hover:border-sky-500/50"
            }`}
            onClick={() => setSelectedMode("MANUAL")}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-sky-500" />
                <span className="font-semibold">Manual</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleMode("m1");
                }}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.find((s) => s.id === "m1")?.isActive ? "bg-sky-500" : "bg-muted"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.find((s) => s.id === "m1")?.isActive ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">Full control over all trading decisions</p>
            {settings.find((s) => s.id === "m1")?.isActive && (
              <div className="mt-3 rounded-md border border-sky-500/20 bg-sky-500/5 p-2">
                <p className="text-[10px] text-sky-700">Active - You can trade anytime</p>
              </div>
            )}
          </div>

          {/* Auto Mode Card */}
          <div
            className={`flex-1 cursor-pointer rounded-lg border-2 p-4 transition-all ${
              selectedMode === "AUTO_BY_AI"
                ? "border-emerald-500 bg-emerald-500/5"
                : "border-muted hover:border-emerald-500/50"
            }`}
            onClick={() => setSelectedMode("AUTO_BY_AI")}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-emerald-500" />
                <span className="font-semibold">AI Auto</span>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  toggleMode("m2");
                }}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.find((s) => s.id === "m2")?.isActive ? "bg-emerald-500" : "bg-muted"
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.find((s) => s.id === "m2")?.isActive ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">AI analyzes market and executes automatically</p>
            {settings.find((s) => s.id === "m2")?.isActive && (
              <div className="mt-3 rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2">
                <p className="text-[10px] text-emerald-700">Active - AI will execute trades</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Current Settings */}
      <div className="rounded-xl border bg-card p-5">
        <h4 className="font-semibold mb-3 flex items-center gap-2">
          <ToggleRight className="h-4 w-4" />
          Current Configuration
        </h4>
        <p className="text-sm text-muted-foreground">{activeSetting.description}</p>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {activeSetting.settings?.maxLotSize !== undefined && (
            <div className="rounded-lg border bg-muted/50 p-3">
              <p className="text-xs text-muted-foreground">Max Lot Size</p>
              <p className="font-mono font-semibold">{activeSetting.settings.maxLotSize}</p>
            </div>
          )}
          {activeSetting.settings?.minLotSize !== undefined && (
            <div className="rounded-lg border bg-muted/50 p-3">
              <p className="text-xs text-muted-foreground">Min Lot Size</p>
              <p className="font-mono font-semibold">{activeSetting.settings.minLotSize}</p>
            </div>
          )}
          {activeSetting.settings?.riskPerTrade !== undefined && (
            <div className="rounded-lg border bg-muted/50 p-3">
              <p className="text-xs text-muted-foreground">Risk Per Trade</p>
              <p className="font-mono font-semibold">{activeSetting.settings.riskPerTrade}%</p>
            </div>
          )}
          {activeSetting.settings?.enabledIndicators && (
            <div className="sm:col-span-2 rounded-lg border bg-muted/50 p-3">
              <p className="text-xs text-muted-foreground mb-2">Enabled Indicators</p>
              <div className="flex flex-wrap gap-1">
                {activeSetting.settings.enabledIndicators.map((indicator) => (
                  <span key={indicator} className="inline-flex items-center rounded px-2 py-0.5 text-xs font-medium bg-primary/10 text-primary">
                    {indicator}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mode Switching Info */}
      <div className="rounded-xl border bg-amber-500/5 p-4">
        <div className="flex items-start gap-2">
          <svg className="h-4 w-4 text-amber-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="text-xs text-amber-700">
            <p className="font-medium">Important Notice</p>
            <ul className="mt-1 list-disc space-y-1 pl-4">
              <li>Switching to Auto mode will disable manual order placement immediately</li>
              <li>Any open positions remain unaffected by mode switching</li>
              <li>Auto mode requires active AI connection and valid token authentication</li>
              <li>You can switch back to Manual mode at any time</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
