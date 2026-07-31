export type DiagnosticNotificationType = "PATTERN" | "RECOMMENDATION" | "VALIDATION";

export interface DiagnosticNotification {
  id: string;
  type: DiagnosticNotificationType;
  title: string;
  detail: string;
  createdAt: string;
  href: string;
  read: boolean;
}

export const diagnosticNotificationsStub: DiagnosticNotification[] = [
  { id: "notification-pattern", type: "PATTERN", title: "New dominant loss pattern", detail: "Counter-trend entries exceeded the high-severity threshold.", createdAt: "2026-07-31T08:20:00Z", href: "/diagnostics/patterns", read: false },
  { id: "notification-recommendation", type: "RECOMMENDATION", title: "Critical control ready", detail: "Trend confirmation recommendation is ready for review.", createdAt: "2026-07-31T07:45:00Z", href: "/diagnostics/recommendations", read: false },
  { id: "notification-validation", type: "VALIDATION", title: "Validation target achieved", detail: "Counter-trend loss share is now below the 30% target.", createdAt: "2026-07-30T16:10:00Z", href: "/diagnostics/improvements", read: true },
];