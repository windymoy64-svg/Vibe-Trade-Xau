import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { StrategyAutoSelection } from "@/pages/StrategyAutoSelection";

describe("StrategyAutoSelection", () => {
  it("renders market context, ranked candidates, and guardrails from preview data", () => {
    render(<MemoryRouter><StrategyAutoSelection /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Auto-selection strategy mode" })).toBeInTheDocument();
    expect(screen.getByText("Preview data")).toBeInTheDocument();
    expect(screen.getAllByText("Evidence trend guard").length).toBeGreaterThan(0);
    expect(screen.getByText("Range mean reversion")).toBeInTheDocument();
    expect(screen.getByText("Selection guardrails")).toBeInTheDocument();
    expect(screen.getByText("Dynamic simulation")).toBeInTheDocument();
    expect(screen.getByText("Selection history")).toBeInTheDocument();
    expect(screen.getByText("Fixed risk management")).toBeInTheDocument();
    expect(screen.getByText("0.5%")).toBeInTheDocument();
    expect(screen.getByText("Conservative fixed")).toBeInTheDocument();
  });

  it("re-evaluates selection in page memory without enabling execution", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><StrategyAutoSelection /></MemoryRouter>);
    await user.click(screen.getByRole("button", { name: "Re-evaluate preview" }));
    expect(screen.getByText("Selection preview only")).toBeInTheDocument();
    expect(screen.getByText(/does not activate a strategy/i)).toBeInTheDocument();
  });

  it("starts and pauses the dynamic preview interval", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><StrategyAutoSelection /></MemoryRouter>);
    await user.click(screen.getByRole("button", { name: "Start simulation" }));
    expect(screen.getByText("RUNNING")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Pause simulation" }));
    expect(screen.getByText("PAUSED")).toBeInTheDocument();
  });
});