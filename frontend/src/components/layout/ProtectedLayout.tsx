import { Navigate, Outlet, useLocation } from "react-router";
import { Layout } from "@/components/layout/Layout";
import { hasDiagnosticMockSession } from "@/lib/diagnosticAuth";

export function ProtectedLayout() {
  const location = useLocation();
  if (!hasDiagnosticMockSession()) {
    const returnTo = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/login?returnTo=${encodeURIComponent(returnTo)}`} replace />;
  }
  if (location.pathname === "/auto-trade") return <Outlet />;
  return <Layout />;
}