import { useState, useEffect } from "react";
import { ConnectionTimeoutConfig } from "@/components/fail-safe/ConnectionTimeoutConfig";

interface Position {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  volume: number;
  entryPrice: number;
  currentPrice: number;
  profitLoss: number;
  sl?: number;
  tp?: number;
}

interface PendingOrder {
  id: string;
  symbol: string;
  type: "BUY_LIMIT" | "SELL_LIMIT" | "BUY_STOP" | "SELL_STOP";
  price: number;
  volume: number;
}

export function FailSafeDashboard() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [pendingOrders, setPendingOrders] = useState<PendingOrder[]>([]);
  const [connectionHistory, setConnectionHistory] = useState<
    Array<{ time: string; status: "connected" | "disconnected"; reason?: string }>
  >([]);

  useEffect(() => {
    const interval = setInterval(() => {
      if (Math.random() > 0.9) {
        // setConnected(false);
        // setLatencyMs(null);
        // setErrorCode(500);
        setConnectionHistory((prev) => [
          ...prev,
          {
            time: new Date().toISOString(),
            status: "disconnected",
            reason: "Simulated connection lost",
          },
        ]);
      } else {
        // setConnected(true);
        // connection ok
        
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleEmergencyClose = () => {
    if (window.confirm("EMERGENCY CLOSE: All positions will be closed immediately. Continue?")) {
      setPositions([]);
      setPendingOrders([]);
      setConnectionHistory((prev) => [
        ...prev,
        { time: new Date().toISOString(), status: "disconnected", reason: "Emergency close triggered" },
      ]);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Fail-Safe Dashboard</h1>
        <button
          onClick={handleEmergencyClose}
          className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors"
        >
          Emergency Close
        </button>
      </header>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Connection Threshold Configuration</h2>
        <ConnectionTimeoutConfig />
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Open Positions ({positions.length})</h2>
        {positions.length === 0 ? (
          <p className="text-slate-500 text-sm">No open positions</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2">Symbol</th>
                <th className="text-left py-2">Side</th>
                <th className="text-right py-2">Volume</th>
                <th className="text-right py-2">Entry Price</th>
                <th className="text-right py-2">Current Price</th>
                <th className="text-right py-2">P/L</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => (
                <tr key={pos.id} className="border-b border-slate-100 last:border-none">
                  <td className="py-2 font-medium">{pos.symbol}</td>
                  <td className={`py-2 ${pos.side === "BUY" ? "text-emerald-600" : "text-red-600"}`}>{pos.side}</td>
                  <td className="text-right py-2">{pos.volume.toFixed(2)} lots</td>
                  <td className="text-right py-2">{pos.entryPrice.toFixed(2)}</td>
                  <td className="text-right py-2">{pos.currentPrice.toFixed(2)}</td>
                  <td className={`text-right py-2 font-semibold ${pos.profitLoss >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {pos.profitLoss >= 0 ? "+" : ""}{pos.profitLoss.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Pending Orders ({pendingOrders.length})</h2>
        {pendingOrders.length === 0 ? (
          <p className="text-slate-500 text-sm">No pending orders</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2">Symbol</th>
                <th className="text-left py-2">Type</th>
                <th className="text-right py-2">Price</th>
                <th className="text-right py-2">Volume</th>
              </tr>
            </thead>
            <tbody>
              {pendingOrders.map((order) => (
                <tr key={order.id} className="border-b border-slate-100 last:border-none">
                  <td className="py-2 font-medium">{order.symbol}</td>
                  <td className="py-2 text-blue-600">{order.type}</td>
                  <td className="text-right py-2">{order.price.toFixed(2)}</td>
                  <td className="text-right py-2">{order.volume.toFixed(2)} lots</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Connection History</h2>
        <div className="space-y-1 max-h-40 overflow-y-auto">
          {connectionHistory.slice(-10).map((event, idx) => (
            <div key={idx} className="flex items-center text-xs">
              <span className="text-slate-500 w-48">{event.time}</span>
              <span className={`font-medium ${event.status === "connected" ? "text-emerald-600" : "text-red-600"}`}>
                {event.status}
              </span>
              {event.reason && (
                <span className="text-slate-400 ml-2 italic">{event.reason}</span>
              )}
            </div>
          ))}
          {connectionHistory.length === 0 && (
            <p className="text-slate-500 text-sm">No connection events yet</p>
          )}
        </div>
      </section>
    </div>
  );
}
