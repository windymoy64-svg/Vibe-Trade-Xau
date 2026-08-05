import { Bot, User, ArrowUpRight } from "lucide-react";

interface ExecutionMetrics {
  totalTrades: number;
  manualTrades: number;
  autoTrades: number;
  winRateManual: number;
  winRateAuto: number;
  profitFactorManual: number;
  profitFactorAuto: number;
}

const mockMetrics: ExecutionMetrics = {
  totalTrades: 48,
  manualTrades: 22,
  autoTrades: 26,
  winRateManual: 54.5,
  winRateAuto: 69.2,
  profitFactorManual: 1.35,
  profitFactorAuto: 1.87,
};

export function OwnershipDashboard() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Ownership & Source Eksekusi</h1>
        <p className="text-slate-500">Last updated: Today, 10:30 AM</p>
      </header>

      <section className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-slate-700">Total Trades</h3>
            <ArrowUpRight className="w-5 h-5 text-emerald-600" />
          </div>
          <p className="text-3xl font-bold text-slate-900">{mockMetrics.totalTrades}</p>
          <p className="text-xs text-slate-500 mt-1">This month</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-slate-700">Manual Trades</h3>
            <User className="w-5 h-5 text-blue-600" />
          </div>
          <p className="text-3xl font-bold text-slate-900">{mockMetrics.manualTrades}</p>
          <p className="text-xs text-slate-500 mt-1">{((mockMetrics.manualTrades / mockMetrics.totalTrades) * 100).toFixed(0)}% of total</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-slate-700">Auto Trades</h3>
            <Bot className="w-5 h-5 text-purple-600" />
          </div>
          <p className="text-3xl font-bold text-slate-900">{mockMetrics.autoTrades}</p>
          <p className="text-xs text-slate-500 mt-1">{((mockMetrics.autoTrades / mockMetrics.totalTrades) * 100).toFixed(0)}% of total</p>
        </div>

        <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg shadow-sm p-6 text-white">
          <h3 className="font-medium opacity-90">Win Rate Gap</h3>
          <p className="text-3xl font-bold mt-2">+14.7%</p>
          <p className="text-sm opacity-90 mt-1">Auto outperforms Manual by {mockMetrics.winRateAuto - mockMetrics.winRateManual}%</p>
        </div>
      </section>

      <section className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-blue-600" />
            Manual Trading Performance
          </h2>
          
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
              <span className="text-slate-700">Win Rate</span>
              <span className={`font-bold ${mockMetrics.winRateManual >= 60 ? "text-emerald-600" : "text-orange-600"}`}>
                {mockMetrics.winRateManual.toFixed(1)}%
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
              <span className="text-slate-700">Profit Factor</span>
              <span className={`font-bold ${mockMetrics.profitFactorManual >= 1.5 ? "text-emerald-600" : "text-orange-600"}`}>
                {mockMetrics.profitFactorManual.toFixed(2)}
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
              <span className="text-slate-700">Avg Hold Time</span>
              <span className="font-bold text-slate-900">4.2 hours</span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
              <span className="text-slate-700">Best Session</span>
              <span className="font-bold text-slate-900">London</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Bot className="w-5 h-5 text-purple-600" />
            AI Auto Trading Performance
          </h2>
          
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
              <span className="text-slate-700">Win Rate</span>
              <span className={`font-bold ${mockMetrics.winRateAuto >= 60 ? "text-emerald-600" : "text-orange-600"}`}>
                {mockMetrics.winRateAuto.toFixed(1)}%
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
              <span className="text-slate-700">Profit Factor</span>
              <span className={`font-bold ${mockMetrics.profitFactorAuto >= 1.5 ? "text-emerald-600" : "text-orange-600"}`}>
                {mockMetrics.profitFactorAuto.toFixed(2)}
              </span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
              <span className="text-slate-700">Avg Hold Time</span>
              <span className="font-bold text-slate-900">2.8 hours</span>
            </div>
            
            <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
              <span className="text-slate-700">Best Session</span>
              <span className="font-bold text-slate-900">New York</span>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Execution Source Distribution</h2>
        
        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <h3 className="font-medium text-slate-700 mb-3">Manual Execution (USER_DRIVEN)</h3>
            <div className="space-y-3">
              {[
                { label: "Technical Analysis Based", value: 65 },
                { label: "News Events", value: 20 },
                { label: "Psychological Trading", value: 10 },
                { label: "Others", value: 5 },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-700">{item.label}</span>
                    <span className="font-semibold text-slate-900">{item.value}%</span>
                  </div>
                  <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-600 rounded-full"
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-medium text-slate-700 mb-3">AI Auto Execution (AUTO_BY_AI)</h3>
            <div className="space-y-3">
              {[
                { label: "ACR Confluence Signals", value: 45 },
                { label: "SMC Structure Breaks", value: 30 },
                { label: "Fibonacci Levels", value: 15 },
                { label: "Session Timing", value: 10 },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-700">{item.label}</span>
                    <span className="font-semibold text-slate-900">{item.value}%</span>
                  </div>
                  <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-purple-600 rounded-full"
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-gradient-to-r from-slate-800 to-slate-900 rounded-lg shadow-sm p-6 text-white">
        <h2 className="text-lg font-semibold mb-4">Key Insights</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <div>
            <p className="font-semibold text-emerald-400">+14.7%</p>
            <p className="text-sm text-slate-300 mt-1">Higher win rate for AI trading vs manual</p>
          </div>
          <div>
            <p className="font-semibold text-blue-400">38%</p>
            <p className="text-sm text-slate-300 mt-1">More trades executed by AI automation</p>
          </div>
          <div>
            <p className="font-semibold text-purple-400">1.87x</p>
            <p className="text-sm text-slate-300 mt-1">Profit factor achieved by AI auto-execution</p>
          </div>
        </div>
      </section>
    </div>
  );
}
