import { Suspense, lazy, type ComponentType } from "react";
import { createBrowserRouter } from "react-router";
import { ProtectedLayout } from "@/components/layout/ProtectedLayout";

const Home = lazy(() => import("@/pages/Home").then((m) => ({ default: m.Home })));
const Agent = lazy(() => import("@/pages/Agent").then((m) => ({ default: m.Agent })));
const RunDetail = lazy(() =>
  import("@/pages/RunDetail").then((m) => ({ default: m.RunDetail })),
);
const Compare = lazy(() =>
  import("@/pages/Compare").then((m) => ({ default: m.Compare })),
);
const Settings = lazy(() =>
  import("@/pages/Settings").then((m) => ({ default: m.Settings })),
);
const Runtime = lazy(() =>
  import("@/pages/Runtime").then((m) => ({ default: m.Runtime })),
);
const Reports = lazy(() =>
  import("@/pages/Reports").then((m) => ({ default: m.Reports })),
);
const Correlation = lazy(() =>
  import("@/pages/Correlation").then((m) => ({ default: m.Correlation })),
);
const AlphaZoo = lazy(() =>
  import("@/pages/AlphaZoo").then((m) => ({ default: m.AlphaZoo })),
);
const DiagnosticsDashboard = lazy(() => import("@/pages/DiagnosticsDashboard").then((m) => ({ default: m.DiagnosticsDashboard })));
const DiagnosticTrades = lazy(() => import("@/pages/DiagnosticTrades").then((m) => ({ default: m.DiagnosticTrades })));
const DiagnosticTradeDetail = lazy(() => import("@/pages/DiagnosticTradeDetail").then((m) => ({ default: m.DiagnosticTradeDetail })));
const DiagnosticFilters = lazy(() => import("@/pages/DiagnosticFilters").then((m) => ({ default: m.DiagnosticFilters })));
const LossPatternAnalysis = lazy(() =>
  import("@/pages/LossPatternAnalysis").then((m) => ({ default: m.LossPatternAnalysis })),
);
const LossPatternsCompare = lazy(() =>
  import("@/pages/LossPatternsCompare").then((m) => ({ default: m.LossPatternsCompare })),
);
const DiagnosticRecommendations = lazy(() =>
  import("@/pages/DiagnosticRecommendations").then((m) => ({ default: m.DiagnosticRecommendations })),
);
const DiagnosticRecommendationDetail = lazy(() =>
  import("@/pages/DiagnosticRecommendationDetail").then((m) => ({ default: m.DiagnosticRecommendationDetail })),
);
const DiagnosticImprovementProgress = lazy(() =>
  import("@/pages/DiagnosticImprovementProgress").then((m) => ({ default: m.DiagnosticImprovementProgress })),
);
const DiagnosticAuth = lazy(() =>
  import("@/pages/DiagnosticAuth").then((m) => ({ default: m.DiagnosticAuth })),
);
const DiagnosticProfileSettings = lazy(() =>
  import("@/pages/DiagnosticProfileSettings").then((m) => ({ default: m.DiagnosticProfileSettings })),
);
const DiagnosticDataSources = lazy(() =>
  import("@/pages/DiagnosticDataSources").then((m) => ({ default: m.DiagnosticDataSources })),
);
const DiagnosticNotificationSettings = lazy(() =>
  import("@/pages/DiagnosticNotificationSettings").then((m) => ({ default: m.DiagnosticNotificationSettings })),
);
const AutoTrade = lazy(() => import("@/pages/AutoTrade").then((m) => ({ default: m.AutoTrade })));
const StrategyAutoSelection = lazy(() => import("@/pages/StrategyAutoSelection").then((m) => ({ default: m.StrategyAutoSelection })));
const PrecisionExecution = lazy(() => import("@/pages/PrecisionExecution").then((m) => ({ default: m.PrecisionExecution })));
const EaBridgeDashboard = lazy(() => import("@/pages/EaBridgeDashboard").then((m) => ({ default: m.EaBridgeDashboard })));
const EaBridgeAuditTrail = lazy(() => import("@/pages/EaBridgeAuditTrail").then((m) => ({ default: m.EaBridgeAuditTrail })));
const EaBridgeReconciliation = lazy(() => import("@/pages/EaBridgeReconciliation").then((m) => ({ default: m.EaBridgeReconciliation })));
const EaBridgeTradeDiagnostics = lazy(() => import("@/pages/EaBridgeTradeDiagnostics").then((m) => ({ default: m.EaBridgeTradeDiagnostics })));
const Mt5ProductionDiagnostics = lazy(() => import("@/pages/Mt5ProductionDiagnostics").then((m) => ({ default: m.Mt5ProductionDiagnostics })));
const PreciseStopLoss = lazy(() => import("@/pages/PreciseStopLoss").then((m) => ({ default: m.PreciseStopLoss })));
const DataFeedPusher = lazy(() => import("@/pages/DataFeedPusher").then((m) => ({ default: m.DataFeedPusher })));

function PageLoader() {
  return (
    <div className="flex h-[60vh] items-center justify-center text-muted-foreground">
      Loading…
    </div>
  );
}

function wrap(Component: ComponentType) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  );
}

export const router = createBrowserRouter([
  { path: "/login", element: wrap(DiagnosticAuth) },
  { path: "/register", element: wrap(DiagnosticAuth) },
  {
    element: <ProtectedLayout />,
    children: [
      { path: "/", element: wrap(Home) },
      { path: "/diagnostics", element: wrap(DiagnosticsDashboard) },
      { path: "/diagnostics/trades", element: wrap(DiagnosticTrades) },
      { path: "/diagnostics/trades/:tradeId", element: wrap(DiagnosticTradeDetail) },
      { path: "/diagnostics/filters", element: wrap(DiagnosticFilters) },
      { path: "/diagnostics/patterns", element: wrap(LossPatternAnalysis) },
      { path: "/diagnostics/patterns/compare", element: wrap(LossPatternsCompare) },
      { path: "/diagnostics/recommendations", element: wrap(DiagnosticRecommendations) },
      { path: "/diagnostics/recommendations/:recommendationId", element: wrap(DiagnosticRecommendationDetail) },
      { path: "/diagnostics/improvements", element: wrap(DiagnosticImprovementProgress) },
      { path: "/diagnostics/settings/profile", element: wrap(DiagnosticProfileSettings) },
      { path: "/diagnostics/settings/data-sources", element: wrap(DiagnosticDataSources) },
      { path: "/diagnostics/settings/notifications", element: wrap(DiagnosticNotificationSettings) },
      { path: "/auto-trade", element: wrap(AutoTrade) },
      { path: "/auto-trade/strategy-selection", element: wrap(StrategyAutoSelection) },
      { path: "/precision-execution", element: wrap(PrecisionExecution) },
      { path: "/ea-bridge", element: wrap(EaBridgeDashboard) },
      { path: "/ea-bridge/audit", element: wrap(EaBridgeAuditTrail) },
      { path: "/ea-bridge/reconciliation", element: wrap(EaBridgeReconciliation) },
      { path: "/ea-bridge/trades/:tradeId", element: wrap(EaBridgeTradeDiagnostics) },
      { path: "/mt5-integration", element: wrap(Mt5ProductionDiagnostics) },
      { path: "/precise-stop-loss", element: wrap(PreciseStopLoss) },
      { path: "/data-feed", element: wrap(DataFeedPusher) },
      { path: "/agent", element: wrap(Agent) },
      { path: "/runtime", element: wrap(Runtime) },
      { path: "/reports", element: wrap(Reports) },
      { path: "/settings", element: wrap(Settings) },
      { path: "/runs/:runId", element: wrap(RunDetail) },
      { path: "/compare", element: wrap(Compare) },
      { path: "/correlation", element: wrap(Correlation) },
      { path: "/alpha-zoo", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/bench", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/compare", element: wrap(AlphaZoo) },
      { path: "/alpha-zoo/:alphaId", element: wrap(AlphaZoo) },
    ],
  },
]);
