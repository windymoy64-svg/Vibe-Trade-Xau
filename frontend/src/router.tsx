import { Suspense, lazy, type ComponentType } from "react";
import { createBrowserRouter } from "react-router";
import { Layout } from "@/components/layout/Layout";

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
const LossPatternAnalysis = lazy(() => import("@/pages/LossPatternAnalysis").then((m) => ({ default: m.LossPatternAnalysis })));

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
  {
    element: <Layout />,
    children: [
      { path: "/", element: wrap(Home) },
      { path: "/diagnostics", element: wrap(DiagnosticsDashboard) },
      { path: "/diagnostics/trades", element: wrap(DiagnosticTrades) },
      { path: "/diagnostics/trades/:tradeId", element: wrap(DiagnosticTradeDetail) },
      { path: "/diagnostics/filters", element: wrap(DiagnosticFilters) },
      { path: "/diagnostics/patterns", element: wrap(LossPatternAnalysis) },
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
