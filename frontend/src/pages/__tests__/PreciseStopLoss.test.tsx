import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { PreciseStopLoss } from "@/pages/PreciseStopLoss";
import { pipsToPoints, pointsToPips, priceDistanceInPips, roundToXauusdPrecision } from "@/data/precise-stop-loss";

describe("PreciseStopLoss", () => {
  it("renders a mock XAUUSD protection signal and validation queue", () => {
    render(<MemoryRouter><PreciseStopLoss /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Precise stop loss signals" })).toBeInTheDocument();
    const primary = screen.getByLabelText("Primary precise stop loss signal");
    expect(primary).toBeInTheDocument();
    expect(within(primary).getByText("XAUUSD · BUY")).toBeInTheDocument();
    expect(within(primary).getAllByText("2382.50")).toHaveLength(2);
    expect(within(primary).getByText("VALID · 94%")).toBeInTheDocument();
    const queue = screen.getByLabelText("Stop loss signal queue");
    expect(queue).toBeInTheDocument();
    expect(within(queue).getByText("REVIEW · 72%")).toBeInTheDocument();
    expect(screen.getByText("Protection candidates remain non-executable until every structural and risk gate passes.")).toBeInTheDocument();
  });

  // Utility tests for XAUUSD pip/point conversion
  it("converts pips to points correctly for XAUUSD (1 pip = 10 points)", () => {
    expect(pipsToPoints(1)).toBe(10);
    expect(pipsToPoints(2.5)).toBe(25);
    expect(pipsToPoints(0.1)).toBe(1);
  });

  it("converts points to pips correctly for XAUUSD", () => {
    expect(pointsToPips(10)).toBe(1);
    expect(pointsToPips(25)).toBe(2.5);
    expect(pointsToPips(1)).toBe(0.1);
  });

  it("calculates price distance in pips correctly for XAUUSD", () => {
    // At 5-digit pricing, 0.10 USD difference = 1 pip
    expect(priceDistanceInPips(2384.85, 2385.95)).toBe(11.0);
    expect(priceDistanceInPips(2390.00, 2390.50)).toBe(5.0);
    expect(priceDistanceInPips(2389.78, 2389.78)).toBe(0.0);
  });

  it("rounds prices to XAUUSD precision (5 digits)", () => {
    expect(roundToXauusdPrecision(2384.8534567)).toBe(2384.85346);
    expect(roundToXauusdPrecision(2392.10000)).toBe(2392.10000);
  });
});
