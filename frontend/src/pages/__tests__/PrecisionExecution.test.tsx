import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { PrecisionExecution } from "@/pages/PrecisionExecution";

vi.mock("@/lib/echarts", () => ({
  echarts: {
    init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
  },
}));

describe("PrecisionExecution", () => {
  it("renders the execution terminal foundation with preview data", () => {
    render(<MemoryRouter><PrecisionExecution /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Precision trading execution" })).toBeInTheDocument();
    expect(screen.getByText("Market data input")).toBeInTheDocument();
    expect(screen.getByText("HTF structure chart")).toBeInTheDocument();
    expect(screen.getByLabelText("HTF candlestick chart with BOS and CHOCH markers")).toBeInTheDocument();
    expect(screen.getByText("LTF Supply / Demand map")).toBeInTheDocument();
    expect(screen.getByLabelText("LTF candlestick chart with Supply and Demand zones")).toBeInTheDocument();
    expect(screen.getByText("SUPPLY")).toBeInTheDocument();
    expect(screen.getByText("DEMAND")).toBeInTheDocument();
    expect(screen.getByText("Bullish R-ACR · low sweep + reclaim")).toBeInTheDocument();
    expect(screen.getByText("Bearish R-ACR · high sweep + reject")).toBeInTheDocument();
    expect(screen.getByText(/2 reversal markers/)).toBeInTheDocument();
    expect(screen.getByText("Bullish FVG · open")).toBeInTheDocument();
    expect(screen.getByText("Bearish FVG · partial")).toBeInTheDocument();
    expect(screen.getByText(/1 FVG confluence/)).toBeInTheDocument();
    expect(screen.getByText("HIGH CONFLUENCE · FVG + ACR")).toBeInTheDocument();
    expect(screen.getByText(/overlaps fresh zone acr-bull-01/)).toBeInTheDocument();
    expect(screen.getByLabelText("ACR zone panel")).toBeInTheDocument();
    expect(screen.getByText("Bullish ACR")).toBeInTheDocument();
    expect(screen.getByText("Bearish ACR")).toBeInTheDocument();
    expect(screen.getByLabelText("bullish zone fresh")).toBeInTheDocument();
    expect(screen.getByLabelText("bearish zone invalid")).toBeInTheDocument();
    expect(screen.getByText("FRESH ZONE")).toBeInTheDocument();
    expect(screen.getByText("INVALID ZONE")).toBeInTheDocument();
    expect(screen.getByLabelText("Fibonacci premium discount panel")).toBeInTheDocument();
    expect(screen.getByText("PREMIUM · SELL AREA")).toBeInTheDocument();
    expect(screen.getByText("DISCOUNT · BUY AREA")).toBeInTheDocument();
    expect(screen.getByText("BUY setup eligible")).toBeInTheDocument();
    const orderRecommendation = screen.getByLabelText("Order type recommendation");
    expect(orderRecommendation).toBeInTheDocument();
    expect(within(orderRecommendation).getByText("BUY LIMIT")).toBeInTheDocument();
    expect(screen.getByText("Mechanical decision checks")).toBeInTheDocument();
    expect(screen.getByText(/Market order stays blocked/)).toBeInTheDocument();
    const preciseEntry = screen.getByLabelText("Precise entry price");
    expect(preciseEntry).toBeInTheDocument();
    expect(within(preciseEntry).getByText("2384.85000")).toBeInTheDocument();
    expect(screen.getByText("5-decimal quote")).toBeInTheDocument();
    expect(screen.getByText(/50% FVG equilibrium/)).toBeInTheDocument();
    const tradeLevels = screen.getByLabelText("Stop loss and multi take profit panel");
    expect(tradeLevels).toBeInTheDocument();
    expect(within(tradeLevels).getByText("2382.50000")).toBeInTheDocument();
    expect(within(tradeLevels).getByText("TP1")).toBeInTheDocument();
    expect(within(tradeLevels).getByText("TP2")).toBeInTheDocument();
    expect(within(tradeLevels).getByText("TP3")).toBeInTheDocument();
    expect(screen.getByLabelText("Dynamic trailing stop visualization")).toBeInTheDocument();
    expect(screen.getByText("ACR trailing-stop path")).toBeInTheDocument();
    expect(screen.getByText("One-way protection:")).toBeInTheDocument();
    expect(screen.getByLabelText("Interactive lot calculator")).toBeInTheDocument();
    expect(screen.getByText("0.42")).toBeInTheDocument();
    expect(screen.getByText("Current setup preview")).toBeInTheDocument();
    expect(screen.getByText("No live order routing")).toBeInTheDocument();
    expect(screen.getByLabelText("Actionable dark mode signal card")).toBeInTheDocument();
    expect(screen.getByText("STRONG BUY")).toBeInTheDocument();
    expect(screen.getByText("Signal confidence")).toBeInTheDocument();
    expect(screen.getByText("Preview signal · no live execution")).toBeInTheDocument();
    expect(screen.getByText("Drop OHLCV data here")).toBeInTheDocument();
  });

  it("starts analysis in page memory and advances the workflow preview", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><PrecisionExecution /></MemoryRouter>);
    expect(screen.getAllByText("ACTIVE")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: /Mulai Ekstrak \/ Analisis Strategy/ }));
    expect(screen.getAllByText("ACTIVE")).toHaveLength(2);
    expect(screen.getByRole("button", { name: /Analysis extracted/ })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Preview analysis complete");
  });

  it("accepts a CSV file in page memory", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><PrecisionExecution /></MemoryRouter>);
    const input = document.querySelector<HTMLInputElement>("#precision-ohlc-file")!;
    await user.upload(input, new File(["time,open,high,low,close"], "xauusd.csv", { type: "text/csv" }));
    expect(screen.getByText("xauusd.csv")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("recalculates lot size from balance and risk", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><PrecisionExecution /></MemoryRouter>);
    await user.clear(screen.getByLabelText("Account balance (USD)"));
    await user.type(screen.getByLabelText("Account balance (USD)"), "20000");
    await user.selectOptions(screen.getByLabelText("Risk per trade"), "2");
    expect(screen.getByText("1.70")).toBeInTheDocument();
    expect(screen.getByText("$400.00")).toBeInTheDocument();
  });
});
