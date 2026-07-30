import type { DiagnosticCause } from "@/components/diagnostics/CommonCauseStats";
import type { CauseDistributionPoint } from "@/components/diagnostics/SuspectedCauseChart";
import type { RecentTrade } from "@/components/diagnostics/RecentTrades";

export const dashboardSummary = {
  totalTrades: 1_248,
  winningTrades: 684,
  losingTrades: 564,
  lossRate: 45.2,
} as const;

export const diagnosticCauses: DiagnosticCause[] = [
  { label: "Counter-trend entry", percentage: 42, colorClass: "bg-rose-500" },
  { label: "Market ranging", percentage: 31, colorClass: "bg-amber-500" },
  { label: "Asia session", percentage: 18, colorClass: "bg-sky-500" },
  { label: "Weak momentum", percentage: 9, colorClass: "bg-violet-500" },
];

export const weeklyCauseDistribution: CauseDistributionPoint[] = [
  { label: "Week 1", wins: 44, losses: 28 },
  { label: "Week 2", wins: 58, losses: 24 },
  { label: "Week 3", wins: 50, losses: 31 },
  { label: "Week 4", wins: 69, losses: 18 },
  { label: "Week 5", wins: 55, losses: 25 },
  { label: "Week 6", wins: 74, losses: 16 },
  { label: "Week 7", wins: 62, losses: 22 },
];

export const recentDiagnosticTrades: RecentTrade[] = [
  { id: "#XAU-1048", time: "Today, 09:42", direction: "BUY", result: "SL", reason: "Counter-trend entry", profitLoss: "−$82.40" },
  { id: "#XAU-1047", time: "Today, 08:15", direction: "SELL", result: "TP", reason: null, profitLoss: "+$146.20" },
  { id: "#XAU-1046", time: "Yesterday, 22:31", direction: "BUY", result: "SL", reason: "Market ranging", profitLoss: "−$64.10" },
  { id: "#XAU-1045", time: "Yesterday, 16:08", direction: "SELL", result: "TP", reason: null, profitLoss: "+$118.60" },
  { id: "#XAU-1044", time: "Yesterday, 09:54", direction: "BUY", result: "SL", reason: "Asia session", profitLoss: "−$51.80" },
];

export const quickDiagnosticInsight = {
  cause: "Counter-trend entries",
  percentage: 42,
  recommendation: "Consider tightening trend confirmation before changing indicator parameters.",
} as const;

export interface DiagnosticsDashboardData {
  summary: {
    totalTrades: number;
    winningTrades: number;
    losingTrades: number;
    lossRate: number;
  };
  causes: DiagnosticCause[];
  weeklyDistribution: CauseDistributionPoint[];
  recentTrades: RecentTrade[];
  insight: {
    cause: string;
    percentage: number;
    recommendation: string;
  };
  contextFilterPercentage: number;
}

export const diagnosticsDashboardStub: DiagnosticsDashboardData = {
  summary: dashboardSummary,
  causes: diagnosticCauses,
  weeklyDistribution: weeklyCauseDistribution,
  recentTrades: recentDiagnosticTrades,
  insight: quickDiagnosticInsight,
  contextFilterPercentage: 73,
};