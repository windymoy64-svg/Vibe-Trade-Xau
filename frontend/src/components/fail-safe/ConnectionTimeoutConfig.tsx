interface ConnectionTimeoutConfigProps {
  latencyThresholdMs?: number;
  reconnectAttempts?: number;
  reconnectDelaySeconds?: number;
}

export function ConnectionTimeoutConfig({
  latencyThresholdMs = 5000,
  reconnectAttempts = 3,
  reconnectDelaySeconds = 5,
}: ConnectionTimeoutConfigProps) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-slate-900">Connection Thresholds</h3>
      
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Latency Threshold (ms)
          </label>
          <input
            type="number"
            defaultValue={latencyThresholdMs}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-slate-500">
            Trigger fail-safe if connection latency exceeds this value
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Reconnection Attempts
          </label>
          <input
            type="number"
            defaultValue={reconnectAttempts}
            min={0}
            max={10}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-slate-500">
            Maximum retry attempts before emergency close
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Reconnect Delay (seconds)
          </label>
          <input
            type="number"
            defaultValue={reconnectDelaySeconds}
            min={1}
            max={60}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-slate-500">
            Wait time between reconnection attempts
          </p>
        </div>

        <div className="flex items-end">
          <button className="inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  );
}
