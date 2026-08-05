import { cn } from "@/lib/utils";

interface ConnectionStatusIndicatorProps {
  connected: boolean;
  latencyMs?: number | null;
  errorBarCode?: number | null;
  errorCode?: number | null;
}

export function ConnectionStatusIndicator({
  connected,
  latencyMs,
  errorCode,
}: ConnectionStatusIndicatorProps) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={cn(
          "h-3 w-3 rounded-full",
          connected ? "bg-emerald-500" : "bg-red-500",
        )}
      />
      <div className="text-sm">
        <span
          className={cn(
            "font-medium",
            connected ? "text-emerald-600" : "text-red-600",
          )}
        >
          {connected ? "Connected" : "Disconnected"}
        </span>
        {latencyMs !== undefined && latencyMs !== null && (
          <span className="ml-2 text-slate-500">
            ({latencyMs}ms)
          </span>
        )}
        {errorCode !== undefined && errorCode !== null && (
          <span className="ml-2 text-orange-600">
            (Error: {errorCode})
          </span>
        )}
      </div>
    </div>
  );
}
