import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import { EaBridgeTradeDiagnostics } from "@/pages/EaBridgeTradeDiagnostics";

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/ea-bridge/trades/:tradeId" element={<EaBridgeTradeDiagnostics />} /></Routes></MemoryRouter>);
}

describe("EaBridgeTradeDiagnostics", () => {
  it("renders MT5 execution truth and entry evidence", () => {
    renderAt("/ea-bridge/trades/ea-trade-1840");
    expect(screen.getByRole("heading", { name: "Trade diagnostic · ticket-98421" })).toBeInTheDocument();
    expect(screen.getByText("RESULT SL")).toBeInTheDocument();
    expect(screen.getByLabelText("Trade failure diagnosis")).toHaveTextContent("Regime filter false positive");
    const marketSnapshot = screen.getByLabelText("Entry market snapshot");
    expect(marketSnapshot).toBeInTheDocument();
    expect(within(marketSnapshot).getByText("Ranging")).toBeInTheDocument();
    expect(screen.getByLabelText("EA trade lifecycle")).toBeInTheDocument();
    expect(screen.getByText("corr-cmd-1840")).toBeInTheDocument();
    expect(screen.getByLabelText("Trade failure pattern summary")).toBeInTheDocument();
    expect(screen.getByText("Counter-trend entry")).toBeInTheDocument();
    expect(screen.getByText("Ranging false positive")).toBeInTheDocument();
    expect(screen.getByText("42 / 44")).toBeInTheDocument();
  });

  it("renders a safe not-found state for unknown trade IDs", () => {
    renderAt("/ea-bridge/trades/unknown");
    expect(screen.getByRole("heading", { name: "Trade diagnostic not found" })).toBeInTheDocument();
    expect(screen.getByText(/No synchronized EA trade matches/)).toBeInTheDocument();
  });
});
