import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";

import SpendingByCategoryChart from "./SpendingByCategoryChart.svelte";

/** @type {import("$lib/dashboard").CategoryTotal[]} */
const TOTALS = [
  { categoryId: 5, categoryName: "Groceries", total: "352.18" },
  { categoryId: 7, categoryName: "Transport", total: "20.00" },
];

describe("SpendingByCategoryChart", () => {
  it("shows each category's name and formatted total in the legend", () => {
    render(SpendingByCategoryChart, { totals: TOTALS });
    expect(
      screen.getByText(
        (content, el) => el?.tagName === "LI" && content.includes("Groceries") && content.includes("352.18"),
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        (content, el) => el?.tagName === "LI" && content.includes("Transport") && content.includes("20.00"),
      ),
    ).toBeTruthy();
  });

  it("shows an empty state when there's no spending this period", () => {
    render(SpendingByCategoryChart, { totals: [] });
    expect(screen.getByText(/aucune dépense enregistrée cette période/i)).toBeTruthy();
  });
});
