import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { Mt5ProductionDiagnostics } from "@/pages/Mt5ProductionDiagnostics";

vi.mock("@/lib/echarts", () => ({ echarts: { init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }) } }));

describe("Mt5ProductionDiagnostics", () => {
  it("renders direct terminal and production evidence health", () => {
    render(<MemoryRouter><Mt5ProductionDiagnostics /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Production diagnostics" })).toBeInTheDocument();
    expect(screen.getByText("Native MetaTrader5 Python")).toBeInTheDocument();
    expect(screen.getByLabelText("MT5 connection indicator")).toBeInTheDocument();
    expect(screen.getByText("Python library")).toBeInTheDocument();
    expect(screen.getByText("MT5 build 4890")).toBeInTheDocument();
    expect(screen.getByText("ICMarketsSC-Demo")).toBeInTheDocument();
    expect(screen.getByLabelText("Live XAUUSD OHLC chart")).toBeInTheDocument();
    expect(screen.getByLabelText("XAUUSD candlestick and tick volume chart")).toBeInTheDocument();
    expect(screen.getByText("STREAMING")).toBeInTheDocument();
    expect(screen.getByLabelText("MT5 diagnostic pipeline")).toBeInTheDocument();
    expect(screen.getByText("Production diagnostics", { selector: "p" })).toBeInTheDocument();
    const tradeList = screen.getByLabelText("MT5 diagnostic trade list");
    expect(tradeList).toBeInTheDocument();
    expect(within(tradeList).getByText("Regime filter false positive")).toBeInTheDocument();
    expect(within(tradeList).getByText("Counter-trend entry")).toBeInTheDocument();
    expect(screen.getByLabelText("MT5 failure pattern summary")).toBeInTheDocument();
    expect(screen.getByText("Production failure patterns")).toBeInTheDocument();
    expect(screen.getByText(/This targets 73.9% of classified losses/)).toBeInTheDocument();
  });

  it("filters the MT5 diagnostic trade list", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><Mt5ProductionDiagnostics /></MemoryRouter>);
    const tradeList = screen.getByLabelText("MT5 diagnostic trade list");
    await user.selectOptions(screen.getByLabelText("Filter trade result"), "TP");
    expect(within(tradeList).getByText("No failure detected")).toBeInTheDocument();
    expect(within(tradeList).queryByText("Counter-trend entry")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Search MT5 diagnostic trades"), "missing-ticket");
    expect(await screen.findByText("No diagnostic trades match the current filters.")).toBeInTheDocument();
  });
});
