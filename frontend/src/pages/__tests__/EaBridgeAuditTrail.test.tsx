import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { EaBridgeAuditTrail } from "@/pages/EaBridgeAuditTrail";

describe("EaBridgeAuditTrail", () => {
  it("renders the synchronized append-only event ledger", () => {
    render(<MemoryRouter><EaBridgeAuditTrail /></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "EA audit trail" })).toBeInTheDocument();
    expect(screen.getByText("Append-only preview")).toBeInTheDocument();
    expect(screen.getByLabelText("EA audit events")).toBeInTheDocument();
    expect(screen.getByText("SL+TP modify")).toBeInTheDocument();
    expect(screen.getByText("corr-cmd-1842")).toBeInTheDocument();
  });

  it("filters events by level and search term", async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><EaBridgeAuditTrail /></MemoryRouter>);
    await user.selectOptions(screen.getByLabelText("Filter audit level"), "ERROR");
    expect(screen.getByText("Move SL to BE")).toBeInTheDocument();
    expect(screen.queryByText("SL+TP modify")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Search audit events"), "does-not-exist");
    expect(await screen.findByText("No audit events match the current filters.")).toBeInTheDocument();
  });
});
