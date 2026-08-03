import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { EaBridgeReconciliation } from "@/pages/EaBridgeReconciliation";

describe("EaBridgeReconciliation", () => {
  it("renders engine and MT5 discrepancies", () => {
    render(<MemoryRouter><EaBridgeReconciliation /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Dashboard vs MT5 positions" })).toBeInTheDocument();
    expect(screen.getByLabelText("Position reconciliation results")).toBeInTheDocument();
    expect(screen.getByText("MISMATCH")).toBeInTheDocument();
    expect(screen.getByText("MISSING_ENGINE")).toBeInTheDocument();
    expect(screen.getByText("MISSING_MT5")).toBeInTheDocument();
    expect(screen.getByLabelText("Reconciliation warning")).toBeInTheDocument();
  });

  it("stages a resolution without claiming MT5 mutation", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><EaBridgeReconciliation /></MemoryRouter>);
    const results = screen.getByLabelText("Position reconciliation results");
    await user.click(within(results).getAllByRole("button", { name: "Stage resolution" })[0]);
    expect(screen.getByRole("status")).toHaveTextContent("Operator approval and backend reconciliation are still required");
    expect(within(results).getByText("Resolution staged in preview")).toBeInTheDocument();
  });
});
