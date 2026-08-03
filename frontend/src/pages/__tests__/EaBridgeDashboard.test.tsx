import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { EaBridgeDashboard } from "@/pages/EaBridgeDashboard";

vi.mock("@/lib/echarts", () => ({
  echarts: {
    init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
  },
}));

describe("EaBridgeDashboard", () => {
  it("renders the EA bridge dashboard foundation with preview data", () => {
    render(<MemoryRouter><EaBridgeDashboard /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "EA bridge dashboard" })).toBeInTheDocument();
    expect(screen.getByText("EA MQL5 bridge")).toBeInTheDocument();
    expect(screen.getByText("Preview only")).toBeInTheDocument();
    expect(screen.getByText("Precision engine bridge")).toBeInTheDocument();
    expect(screen.getByLabelText("EA connection dashboard")).toBeInTheDocument();
    expect(screen.getByText("EA · Terminal A")).toBeInTheDocument();
    expect(screen.getByText("EA · VPS Replication")).toBeInTheDocument();
    expect(screen.getByText("EA · Alpari-ECN")).toBeInTheDocument();
    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByText("Offline")).toBeInTheDocument();
    expect(screen.getByText("Syncing")).toBeInTheDocument();
    expect(screen.getByText("2 of 3 connected")).toBeInTheDocument();
    expect(screen.getByLabelText("EA fail-safe protection")).toBeInTheDocument();
    expect(screen.getByText("Fail-safe nominal")).toBeInTheDocument();
    expect(screen.getByLabelText("EA order control panel")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Buy market" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sell market" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Modify SL / TP" })).toBeInTheDocument();
    const livePrice = screen.getByLabelText("Live XAUUSD price");
    expect(livePrice).toBeInTheDocument();
    expect(screen.getByText("LIVE FEED")).toBeInTheDocument();
    expect(within(livePrice).getByText("2389.78")).toBeInTheDocument();
    expect(within(livePrice).getByText("2389.98")).toBeInTheDocument();
    const terminalStatus = screen.getByLabelText("EA terminal connection status");
    expect(terminalStatus).toBeInTheDocument();
    expect(within(terminalStatus).getByText("DEGRADED")).toBeInTheDocument();
    expect(within(terminalStatus).getByText("1 online · 1 syncing · 1 offline")).toBeInTheDocument();
    expect(screen.getByLabelText("Synchronized execution audit")).toBeInTheDocument();
    expect(screen.getByText("SL+TP modify")).toBeInTheDocument();
    expect(screen.getByText("REJECTED")).toBeInTheDocument();
    expect(screen.getByLabelText("Live open MT5 positions")).toBeInTheDocument();
    expect(screen.getByText("ticket-99712")).toBeInTheDocument();
    expect(screen.getByText("ticket-99718")).toBeInTheDocument();
    expect(screen.getAllByText("EA Terminal A").length).toBeGreaterThan(0);
    expect(screen.getAllByText("SYNCED")).toHaveLength(2);
    expect(screen.getByLabelText("Live pending MT5 orders")).toBeInTheDocument();
    expect(screen.getByText("ticket-8821 · EA Terminal A")).toBeInTheDocument();
    expect(screen.getByText("BUY LIMIT")).toBeInTheDocument();
    expect(screen.getByText("SELL STOP")).toBeInTheDocument();
    expect(screen.getAllByText("XAUUSD").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("EA activity log")).toBeInTheDocument();
  });

  it("expands the activity log on demand", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><EaBridgeDashboard /></MemoryRouter>);
    expect(screen.queryByText(/M5 feed streamed every/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Engine activity log/ }));
    expect(screen.getByText(/M5 feed streamed every 1000ms/)).toBeInTheDocument();
    expect(screen.getByText(/Handshake ok · token validated/)).toBeInTheDocument();
  });

  it("logs a preview sync event on refresh", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><EaBridgeDashboard /></MemoryRouter>);
    await user.click(screen.getByRole("button", { name: "Refresh sync" }));
    await user.click(screen.getByRole("button", { name: /Engine activity log/ }));
    expect(screen.getByText(/Manual sync requested/)).toBeInTheDocument();
  });

  it("stages order controls without routing a live trade", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><EaBridgeDashboard /></MemoryRouter>);
    await user.click(screen.getByRole("button", { name: "Modify SL / TP" }));
    await user.click(screen.getByRole("button", { name: /Engine activity log/ }));
    expect(screen.getByText(/MODIFY protection SL/)).toHaveTextContent("No MT5 order was sent");
    await user.click(screen.getByRole("button", { name: "Close position" }));
    const closeDialog = screen.getByRole("alertdialog");
    expect(closeDialog).toBeInTheDocument();
    await user.click(within(closeDialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("stages a pending order cancellation without mutating MT5", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><EaBridgeDashboard /></MemoryRouter>);
    const pendingOrders = screen.getByLabelText("Live pending MT5 orders");
    await user.click(within(pendingOrders).getAllByRole("button", { name: "Cancel" })[0]);
    expect(within(pendingOrders).getByText("CANCEL_REQUESTED")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Engine activity log/ }));
    expect(screen.getByText(/pending order remains active in MT5/)).toBeInTheDocument();
  });
});
