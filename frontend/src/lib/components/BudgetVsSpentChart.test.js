import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";

import BudgetVsSpentChart from "./BudgetVsSpentChart.svelte";

/** @type {import("$lib/dashboard").BudgetVsSpentRow[]} */
const ROWS = [
  {
    categoryId: 5,
    categoryName: "Groceries",
    amount: "400.00",
    spent: "352.18",
    remaining: "47.82",
    status: "warning",
  },
  {
    categoryId: 7,
    categoryName: "Transport",
    amount: "100.00",
    spent: "20.00",
    remaining: "80.00",
    status: "ok",
  },
];

describe("BudgetVsSpentChart", () => {
  it("shows an icon+text status legend, not color alone", async () => {
    render(BudgetVsSpentChart, { rows: ROWS });
    expect(await screen.findByText("Approaching limit")).toBeTruthy();
    expect(await screen.findByText("On track")).toBeTruthy();
  });

  it("shows an empty state when there are no budgets", () => {
    render(BudgetVsSpentChart, { rows: [] });
    expect(screen.getByText(/no budgets yet/i)).toBeTruthy();
  });
});
