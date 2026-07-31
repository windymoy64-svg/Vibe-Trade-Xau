const MOCK_SESSION_KEY = "vibe_diagnostics_mock_session";

export function hasDiagnosticMockSession(): boolean {
  return window.sessionStorage.getItem(MOCK_SESSION_KEY) === "active";
}

export function startDiagnosticMockSession(): void {
  window.sessionStorage.setItem(MOCK_SESSION_KEY, "active");
}

export function clearDiagnosticMockSession(): void {
  window.sessionStorage.removeItem(MOCK_SESSION_KEY);
}