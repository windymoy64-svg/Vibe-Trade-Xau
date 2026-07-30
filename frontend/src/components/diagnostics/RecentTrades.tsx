import { ArrowDownRight, ArrowUpRight, ChevronRight } from "lucide-react";
import { Link } from "react-router";

export interface RecentTrade {
  id: string;
  time: string;
  direction: "BUY" | "SELL";
  result: "TP" | "SL";
  reason: string | null;
  profitLoss: string;
}

interface RecentTradesProps {
  trades: RecentTrade[];
  viewAllHref?: string;
}

export function RecentTrades({ trades, viewAllHref = "/diagnostics/trades" }: RecentTradesProps) {
  return (
    <section className="rounded-xl border bg-card shadow-sm" aria-labelledby="recent-trades-title">
      <div className="flex items-center justify-between border-b p-5">
        <div>
          <h2 id="recent-trades-title" className="font-semibold">Recent trades</h2>
          <p className="mt-1 text-xs text-muted-foreground">Latest entries with quick diagnosis</p>
        </div>
        <Link to={viewAllHref} className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
          View all <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[680px] w-full text-left text-sm">
          <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
            <tr><th className="px-5 py-3">Trade</th><th className="px-5 py-3">Direction</th><th className="px-5 py-3">Result</th><th className="px-5 py-3">Suspected reason</th><th className="px-5 py-3 text-right">P/L</th></tr>
          </thead>
          <tbody className="divide-y">
            {trades.map((trade) => {
              const won = trade.result === "TP";
              return <tr key={trade.id} className="hover:bg-muted/30">
                <td className="px-5 py-4"><div className="font-mono text-xs font-medium">{trade.id}</div><div className="mt-1 text-xs text-muted-foreground">{trade.time}</div></td>
                <td className="px-5 py-4"><span className={`inline-flex items-center gap-1 text-xs font-semibold ${trade.direction === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>{trade.direction === "BUY" ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}{trade.direction}</span></td>
                <td className="px-5 py-4"><span className={`rounded-full px-2 py-1 text-xs font-medium ${won ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>{trade.result}</span></td>
                <td className="px-5 py-4 text-muted-foreground">{trade.reason ?? "—"}</td>
                <td className={`px-5 py-4 text-right font-mono text-xs font-medium ${won ? "text-emerald-500" : "text-rose-500"}`}>{trade.profitLoss}</td>
              </tr>;
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}