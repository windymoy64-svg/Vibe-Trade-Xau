import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { DataFeedPusher } from "@/pages/DataFeedPusher";

describe("DataFeedPusher", () => {
  it("renders the data feed page with preview data", () => {
    render(<MemoryRouter><DataFeedPusher /></MemoryRouter>);

    // Page title
    expect(screen.getByText(/data feed pusher/i)).toBeInTheDocument();

    // Key sections present
    const bodyText = document.body.textContent || "";
    expect(bodyText).toContain("MT5");
    expect(bodyText).toContain("XAUUSD");
    expect(bodyText.toLowerCase()).toContain("live");
    expect(bodyText).toContain("Time");
    expect(bodyText).toContain("Open");
    expect(bodyText).toContain("High");
    expect(bodyText).toContain("Low");
    expect(bodyText).toContain("Close");
    expect(bodyText).toContain("Volume");
    expect(bodyText).toContain("Total Bars");
    expect(bodyText).toContain("Total Ticks");
    expect(bodyText).toContain("Avg Latency");
    expect(bodyText).toContain("Preview only");
    expect(bodyText.toLowerCase()).toContain("no live mt5 connection established");

    // Refresh button exists
    const refreshBtn = screen.getByRole("button", { name: /refresh/i });
    expect(refreshBtn).toBeInTheDocument();
  });
});
