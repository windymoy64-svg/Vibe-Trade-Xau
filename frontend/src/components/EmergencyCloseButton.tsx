import { useState } from "react";
import { AlertTriangle, Shield, X, CheckCircle2 } from "lucide-react";

type PositionStatus = "open" | "closed" | "closing";

interface OpenPosition {
  id: string;
  symbol: string;
  side: "BUY" | "SELL";
  volume: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  status: PositionStatus;
}

const mockPositions: OpenPosition[] = [
  { id: "POS-001", symbol: "XAUUSD", side: "BUY", volume: 0.1, entryPrice: 2348.50, currentPrice: 2352.00, pnl: 35.00, status: "open" },
  { id: "POS-002", symbol: "XAUUSD", side: "SELL", volume: 0.15, entryPrice: 2352.00, currentPrice: 2350.50, pnl: 22.50, status: "open" },
];

export function EmergencyCloseButton() {
  const [positions, setPositions] = useState<OpenPosition[]>(mockPositions);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<OpenPosition | null>(null);
  const [confirmReason, setConfirmReason] = useState("");

  const openEmergencyClose = (position: OpenPosition) => {
    setSelectedPosition(position);
    setShowConfirmModal(true);
  };

  const handleConfirmClose = () => {
    if (!selectedPosition || !confirmReason.trim()) return;

    setPositions((prev) =>
      prev.map((p) =>
        p.id === selectedPosition.id ? { ...p, status: "closing" } : p
      )
    );

    setTimeout(() => {
      setPositions((prev) => prev.filter((p) => p.id !== selectedPosition.id));
      setShowConfirmModal(false);
      setSelectedPosition(null);
      setConfirmReason("");
    }, 1500);
  };

  const handleCloseModal = () => {
    setShowConfirmModal(false);
    setSelectedPosition(null);
    setConfirmReason("");
  };

  const getPositionTone = (pnl: number) => {
    if (pnl >= 0) return "text-emerald-500";
    return "text-rose-500";
  };

  return (
    <div className="space-y-4">
      <h3 className="font-semibold flex items-center gap-2">
        <Shield className="h-5 w-5 text-primary" />
        Active Positions
      </h3>

      {/* Position Cards */}
      <div className="space-y-3">
        {positions.map((position) => (
          <div key={position.id} className="rounded-xl border bg-card p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-lg font-bold text-white ${
                    position.side === "BUY" ? "bg-emerald-500" : "bg-rose-500"
                  }`}
                >
                  {position.side === "BUY" ? "↑" : "↓"}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold">{position.symbol}</span>
                    <span className="inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold bg-muted text-muted-foreground">
                      {position.id}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                    <span>{position.volume.toFixed(2)} lots</span>
                    <span>•</span>
                    <span>Entry: ${position.entryPrice.toFixed(2)}</span>
                    <span>•</span>
                    <span>Current: ${position.currentPrice.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              <div className="sm:self-center">
                <div className="text-right">
                  <p className={`font-mono font-semibold ${getPositionTone(position.pnl)}`}>
                    {position.pnl >= 0 ? "+" : ""}{position.pnl.toFixed(2)} USD
                  </p>
                  <p className="text-[10px] text-muted-foreground">Unrealized P/L</p>
                </div>
              </div>
            </div>

            {/* Emergency Close Button */}
            <div className="mt-4 flex justify-end">
              <button
                onClick={() => openEmergencyClose(position)}
                className="inline-flex items-center gap-2 rounded-lg bg-rose-500 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500/90"
              >
                <AlertTriangle className="h-4 w-4" />
                Emergency Close
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {positions.length === 0 && (
        <div className="rounded-xl border border-dashed p-12 text-center">
          <Shield className="mx-auto h-10 w-10 text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">No active positions</p>
          <p className="text-xs text-muted-foreground mt-1">All positions have been closed</p>
        </div>
      )}

      {/* Confirmation Modal */}
      {showConfirmModal && selectedPosition && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border bg-card p-6 shadow-xl">
            <div className="mb-4 flex items-start justify-between">
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-rose-500/10 p-2">
                  <AlertTriangle className="h-6 w-6 text-rose-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Emergency Close Confirmation</h3>
                  <p className="text-sm text-muted-foreground">This action cannot be undone</p>
                </div>
              </div>
              <button onClick={handleCloseModal} className="rounded p-1 hover:bg-muted">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Position Summary */}
            <div className="mb-4 rounded-lg border bg-muted/50 p-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Symbol</p>
                  <p className="font-semibold">{selectedPosition.symbol}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Side</p>
                  <p className={`font-semibold ${selectedPosition.side === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>
                    {selectedPosition.side}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Volume</p>
                  <p className="font-semibold">{selectedPosition.volume.toFixed(2)} lots</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Current P/L</p>
                  <p className={`font-semibold ${getPositionTone(selectedPosition.pnl)}`}>
                    {selectedPosition.pnl >= 0 ? "+" : ""}{selectedPosition.pnl.toFixed(2)} USD
                  </p>
                </div>
              </div>
            </div>

            {/* Reason Input */}
            <div className="mb-4">
              <label htmlFor="reason" className="mb-1 block text-sm font-medium">
                Reason for Emergency Close
              </label>
              <textarea
                id="reason"
                value={confirmReason}
                onChange={(e) => setConfirmReason(e.target.value)}
                placeholder="Enter reason (required)..."
                rows={3}
                className="w-full rounded-md border bg-muted/50 px-3 py-2 text-sm focus:border-primary focus:outline-none"
              />
            </div>

            {/* Warning Banner */}
            <div className="mb-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5" />
                <div className="text-xs text-amber-700">
                  <p className="font-medium">Warning</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4">
                    <li>All pending orders will be cancelled</li>
                    <li>Position will close at current market price</li>
                    <li>Action will be logged for audit purposes</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleCloseModal}
                disabled={!confirmReason.trim()}
                className="flex-1 rounded-lg border bg-card px-4 py-2.5 text-sm font-semibold hover:bg-muted disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmClose}
                disabled={!confirmReason.trim()}
                className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-rose-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-rose-500/90 disabled:opacity-50"
              >
                <X className="h-4 w-4" />
                Confirm Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Notification */}
      {positions.some(p => p.status === "closing") && (
        <div className="fixed bottom-4 right-4 z-50 rounded-lg bg-emerald-500 px-4 py-3 text-sm text-white shadow-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" />
            <span>Emergency close in progress...</span>
          </div>
        </div>
      )}
    </div>
  );
}
