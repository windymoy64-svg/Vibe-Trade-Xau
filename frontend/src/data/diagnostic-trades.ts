export interface DiagnosticTradeListItem {
  id: string;
  ticketId: string;
  pair: string;
  entryTime: string;
  direction: "BUY" | "SELL";
  result: "TP" | "SL";
  marketRegime: "TRENDING" | "RANGING" | "BREAKOUT";
  session: "ASIA" | "LONDON" | "NEW_YORK";
  suspectedReason: string | null;
  profitLoss: number;
  trendStatus: "BULLISH" | "BEARISH" | "FLAT";
  emaAlignment: "BULLISH" | "BEARISH" | "MIXED";
  rsiValue: number;
  atrValue: number;
  volumeStatus: "NORMAL" | "HIGH" | "LOW";
}

export const diagnosticTradeListStub: DiagnosticTradeListItem[] = [
  { id: "trade_1048", ticketId: "XAU-1048", pair: "XAUUSD", entryTime: "2026-07-30T09:42:00Z", direction: "BUY", result: "SL", marketRegime: "RANGING", session: "ASIA", suspectedReason: "Counter-trend entry", profitLoss: -82.4, trendStatus: "BEARISH", emaAlignment: "MIXED", rsiValue: 61, atrValue: 3.42, volumeStatus: "NORMAL" },
  { id: "trade_1047", ticketId: "XAU-1047", pair: "XAUUSD", entryTime: "2026-07-30T08:15:00Z", direction: "SELL", result: "TP", marketRegime: "TRENDING", session: "LONDON", suspectedReason: null, profitLoss: 146.2, trendStatus: "BEARISH", emaAlignment: "BEARISH", rsiValue: 38, atrValue: 4.1, volumeStatus: "HIGH" },
  { id: "trade_1046", ticketId: "XAU-1046", pair: "XAUUSD", entryTime: "2026-07-29T22:31:00Z", direction: "BUY", result: "SL", marketRegime: "RANGING", session: "NEW_YORK", suspectedReason: "Market ranging", profitLoss: -64.1, trendStatus: "FLAT", emaAlignment: "MIXED", rsiValue: 52, atrValue: 2.28, volumeStatus: "LOW" },
  { id: "trade_1045", ticketId: "XAU-1045", pair: "XAUUSD", entryTime: "2026-07-29T16:08:00Z", direction: "SELL", result: "TP", marketRegime: "BREAKOUT", session: "LONDON", suspectedReason: null, profitLoss: 118.6, trendStatus: "BEARISH", emaAlignment: "BEARISH", rsiValue: 41, atrValue: 5.12, volumeStatus: "HIGH" },
  { id: "trade_1044", ticketId: "XAU-1044", pair: "XAUUSD", entryTime: "2026-07-29T09:54:00Z", direction: "BUY", result: "SL", marketRegime: "RANGING", session: "ASIA", suspectedReason: "Asia session", profitLoss: -51.8, trendStatus: "FLAT", emaAlignment: "BULLISH", rsiValue: 58, atrValue: 1.94, volumeStatus: "LOW" },
  { id: "trade_1043", ticketId: "XAU-1043", pair: "XAUUSD", entryTime: "2026-07-28T18:20:00Z", direction: "BUY", result: "TP", marketRegime: "TRENDING", session: "NEW_YORK", suspectedReason: null, profitLoss: 91.3, trendStatus: "BULLISH", emaAlignment: "BULLISH", rsiValue: 63, atrValue: 3.88, volumeStatus: "NORMAL" },
  { id: "trade_1042", ticketId: "XAU-1042", pair: "XAUUSD", entryTime: "2026-07-28T12:11:00Z", direction: "SELL", result: "SL", marketRegime: "BREAKOUT", session: "LONDON", suspectedReason: "Weak momentum", profitLoss: -73.6, trendStatus: "BEARISH", emaAlignment: "BEARISH", rsiValue: 49, atrValue: 4.65, volumeStatus: "LOW" },
  { id: "trade_1041", ticketId: "XAU-1041", pair: "XAUUSD", entryTime: "2026-07-28T06:47:00Z", direction: "SELL", result: "TP", marketRegime: "TRENDING", session: "ASIA", suspectedReason: null, profitLoss: 104.8, trendStatus: "BEARISH", emaAlignment: "BEARISH", rsiValue: 36, atrValue: 3.05, volumeStatus: "NORMAL" },
];