import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { AutoTrade } from "@/pages/AutoTrade";

describe("AutoTrade", () => {
  it("renders preview controls, metrics, and logs", () => {
    render(<AutoTrade />);
    expect(screen.getByRole("heading", { name: "Execution control center" })).toBeInTheDocument();
    expect(screen.getByText("Preview only")).toBeInTheDocument();
    expect(screen.getByText("Engine controls")).toBeInTheDocument();
    expect(screen.getByText("Real-time execution log")).toBeInTheDocument();
    expect(screen.getByText("Robot controls")).toBeInTheDocument();
    expect(screen.getByText("Current trade execution")).toBeInTheDocument();
    expect(screen.getByText(/PREVIEW-1842/)).toBeInTheDocument();
    expect(screen.getByText("+0.93R")).toBeInTheDocument();
    expect(screen.getByText("No live execution")).toBeInTheDocument();
  });

  it("filters and pauses the execution log preview stream", async () => {
    const user = userEvent.setup();
    render(<AutoTrade />);
    await user.click(screen.getByRole("button", { name: "RISK" }));
    expect(screen.getByText(/Risk gate confirmed/)).toBeInTheDocument();
    expect(screen.queryByText(/Paper engine initialized/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Pause stream" }));
    expect(screen.getByRole("button", { name: "Resume stream" })).toBeInTheDocument();
  });

  it("updates robot activation and applies lot, SL, and TP to page memory", async () => {
    const user = userEvent.setup();
    render(<AutoTrade />);
    const activation = screen.getByRole("switch", { name: "Robot activation" });
    await user.click(activation);
    expect(activation).toHaveAttribute("aria-checked", "true");
    await user.clear(screen.getByLabelText("Lot size"));
    await user.type(screen.getByLabelText("Lot size"), "0.1");
    await user.clear(screen.getByLabelText("Stop loss"));
    await user.type(screen.getByLabelText("Stop loss"), "35");
    await user.clear(screen.getByLabelText("Take profit"));
    await user.type(screen.getByLabelText("Take profit"), "70");
    await user.click(screen.getByRole("button", { name: "Apply preview controls" }));
    expect(screen.getByText("Robot controls applied to page memory.")).toBeInTheDocument();
    expect(screen.getByText(/0.10 lot, SL 35 pips, TP 70 pips/)).toBeInTheDocument();
  });

  it("updates preview status without calling a backend", async () => {
    const user = userEvent.setup();
    render(<AutoTrade />);
    await user.click(screen.getByRole("button", { name: "Start preview" }));
    expect(screen.getByText("RUNNING")).toBeInTheDocument();
    expect(screen.getByText(/Preview engine changed to running/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Emergency stop" }));
    expect(screen.getByText("STOPPED")).toBeInTheDocument();
  });

  it("keeps the mock API key in component state", async () => {
    const user = userEvent.setup();
    render(<AutoTrade />);
    const input = screen.getByLabelText("API key");
    await user.type(input, "preview-key-123");
    await user.click(screen.getByRole("button", { name: "Test connection" }));
    expect(screen.getByText("Preview connection verified for this page session.")).toBeInTheDocument();
    expect(screen.getByText("CONNECTED")).toBeInTheDocument();
    expect(window.localStorage.getItem("auto-trade-api-key")).toBeNull();
    expect(window.sessionStorage.getItem("auto-trade-api-key")).toBeNull();
  });

  it("shows a deterministic preview connection failure", async () => {
    const user = userEvent.setup();
    render(<AutoTrade />);
    await user.type(screen.getByLabelText("API key"), "invalid-preview-key");
    await user.click(screen.getByRole("button", { name: "Test connection" }));
    expect(screen.getByText("ERROR")).toBeInTheDocument();
    expect(screen.getByText(/Preview connection failed/)).toBeInTheDocument();
  });
});
