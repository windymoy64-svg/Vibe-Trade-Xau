import { useState } from "react";
import { Upload, Play, FileText, Clock, Target, TrendingUp, AlertCircle, Download } from "lucide-react";

interface BacktestResult {
  winRate: number;
  profitFactor: number;
  totalTrades: number;
  maxDrawdown: number;
  SharpeRatio: number;
}

const mockBacktestResult: BacktestResult = {
  winRate: 67.3,
  profitFactor: 1.92,
  totalTrades: 156,
  maxDrawdown: -8.4,
  SharpeRatio: 1.45,
};

export default function BacktestEnginePage() {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [csvFile, setCsvFile] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".csv")) {
      setCsvFile(file.name);
      setUploading(true);
      
      setTimeout(() => {
        setUploading(false);
      }, 1500);
    }
  };

  const handleRunBacktest = () => {
    if (!csvFile) return;
    setRunning(true);
    
    setTimeout(() => {
      setRunning(false);
    }, 2000);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Historical Backtest Engine</h1>
        <p className="text-slate-500">Test strategies on historical data</p>
      </header>

      {/* Upload Section */}
      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Upload className="w-5 h-5 text-blue-600" />
          Import Trade Data
        </h2>

        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
            dragging
              ? "border-blue-500 bg-blue-50"
              : uploading
              ? "border-emerald-500 bg-emerald-50"
              : csvFile
              ? "border-emerald-500 bg-emerald-50"
              : "border-slate-300 hover:border-slate-400"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {uploading ? (
            <div className="space-y-2">
              <Clock className="w-12 h-12 text-emerald-600 mx-auto animate-spin" />
              <p className="text-slate-600">Importing {csvFile}...</p>
            </div>
          ) : csvFile ? (
            <div className="space-y-2">
              <FileText className="w-12 h-12 text-emerald-600 mx-auto" />
              <p className="font-medium text-slate-900">{csvFile}</p>
              <p className="text-sm text-slate-500">Ready for backtesting</p>
            </div>
          ) : (
            <div className="space-y-2">
              <Upload className="w-12 h-12 text-slate-400 mx-auto" />
              <p className="text-slate-600 font-medium">
                Drop CSV file here or click to browse
              </p>
              <p className="text-sm text-slate-500">
                Format: ticket_id,symbol,direction,entry_price,exit_price,volume,timestamp
              </p>
              <button className="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
                Browse Files
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Configuration */}
      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-purple-600" />
          Strategy Parameters
        </h2>

        <div className="grid md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Risk Per Trade (%)</label>
            <input type="number" defaultValue={1.5} min={0.1} max={10} step={0.1} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Take Profit (ATR Multiplier)</label>
            <input type="number" defaultValue={2.0} min={0.5} max={10} step={0.1} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Stop Loss (ATR Multiplier)</label>
            <input type="number" defaultValue={1.0} min={0.5} max={5} step={0.1} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={handleRunBacktest}
            disabled={!csvFile || running}
            className={`inline-flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
              !csvFile || running
                ? "bg-slate-300 text-slate-500 cursor-not-allowed"
                : "bg-purple-600 hover:bg-purple-700 text-white"
            }`}
          >
            {running ? (
              <>
                <Clock className="w-5 h-5 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Run Backtest
              </>
            )}
          </button>
          
          <button className="inline-flex items-center gap-2 px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-medium transition-colors">
            <Download className="w-4 h-4" />
            Save Template
          </button>
        </div>
      </section>

      {/* Results */}
      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-emerald-600" />
          Backtest Results
        </h2>

        {running ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-slate-500">
              <Clock className="w-5 h-5 animate-spin" />
              <span>Analyzing trades on ACR/SMC strategy...</span>
            </div>
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div className="h-full bg-purple-600 animate-pulse w-1/2" />
            </div>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
              <h3 className="text-sm font-medium text-emerald-900">Win Rate</h3>
              <p className="text-2xl font-bold text-emerald-700 mt-1">{mockBacktestResult.winRate.toFixed(1)}%</p>
            </div>
            
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <h3 className="text-sm font-medium text-blue-900">Profit Factor</h3>
              <p className="text-2xl font-bold text-blue-700 mt-1">{mockBacktestResult.profitFactor.toFixed(2)}</p>
            </div>
            
            <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
              <h3 className="text-sm font-medium text-purple-900">Total Trades</h3>
              <p className="text-2xl font-bold text-purple-700 mt-1">{mockBacktestResult.totalTrades}</p>
            </div>
            
            <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
              <h3 className="text-sm font-medium text-orange-900">Max Drawdown</h3>
              <p className="text-2xl font-bold text-orange-700 mt-1">{mockBacktestResult.maxDrawdown}%</p>
            </div>
            
            <div className="p-4 bg-cyan-50 rounded-lg border border-cyan-200">
              <h3 className="text-sm font-medium text-cyan-900">Sharpe Ratio</h3>
              <p className="text-2xl font-bold text-cyan-700 mt-1">{mockBacktestResult.SharpeRatio.toFixed(2)}</p>
            </div>
          </div>
        )}

        {!csvFile && (
          <div className="flex items-center gap-2 p-4 bg-slate-50 rounded-lg border border-slate-200">
            <AlertCircle className="w-5 h-5 text-slate-400" />
            <p className="text-sm text-slate-500">No data loaded. Import a CSV file to see results.</p>
          </div>
        )}
      </section>
    </div>
  );
}