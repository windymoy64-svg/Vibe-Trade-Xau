import { Navigate, useLocation } from "react-router";
import { Layout } from "@/components/layout/Layout";
import { hasDiagnosticMockSession } from "@/lib/diagnosticAuth";

export function ProtectedLayout() {
  const location = useLocation();
  if (!hasDiagnosticMockSession()) {
    const returnTo = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/login?returnTo=${encodeURIComponent(returnTo)}`} replace />;
  }
  return <Layout />;
}