import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";

import SpendingTrendChart from "./SpendingTrendChart.svelte";

describe("SpendingTrendChart", () => {
  it("renders the chart when there's spending in the window", () => {
    /** @type {import("$lib/dashboard").DailyTotal[]} */
    const daily = [
      { date: "2026-10-06", total: "0" },
      { date: "2026-10-07", total: "10.00" },
      { date: "2026-10-08", total: "0" },
    ];
    render(SpendingTrendChart, { daily });
    expect(screen.getByRole("heading", { name: /30 derniers jours/i })).toBeTruthy();
    expect(screen.queryByText(/aucune dépense enregistrée/i)).toBeNull();
  });

  it("shows an empty state when every day in the window is zero", () => {
    /** @type {import("$lib/dashboard").DailyTotal[]} */
    const daily = [
      { date: "2026-10-06", total: "0" },
      { date: "2026-10-07", total: "0" },
    ];
    render(SpendingTrendChart, { daily });
    expect(screen.getByText(/aucune dépense enregistrée au cours des 30 derniers jours/i)).toBeTruthy();
  });
});
