export interface DiagnosticProfile {
  id: string;
  name: string;
  email: string;
  role: string;
  timezone: string;
  tradingFocus: string;
  bio: string;
  joinedAt: string;
  lastActiveAt: string;
}

export const diagnosticProfileStub: DiagnosticProfile = {
  id: "usr_preview_trader",
  name: "Alex Morgan",
  email: "alex.morgan@example.com",
  role: "Strategy owner",
  timezone: "Asia/Jakarta",
  tradingFocus: "XAUUSD intraday",
  bio: "Validating evidence-based controls for trend, regime, and session risk.",
  joinedAt: "2026-05-14T08:00:00Z",
  lastActiveAt: "2026-07-31T08:30:00Z",
};