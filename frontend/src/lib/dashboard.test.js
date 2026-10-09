import { describe, it, expect } from "vitest";

import {
  budgetVsSpentRows,
  currentMonthWindow,
  last30DaysWindow,
  spendingByCategory,
  dailyTotals,
  toPlotNumber,
} from "./dashboard.js";

const CATEGORY_NAMES = new Map([
  [1, "Groceries"],
  [2, "Transport"],
]);

describe("budgetVsSpentRows", () => {
  it("maps each budget to a row, never recomputing spent/remaining/status", () => {
    /** @type {Parameters<typeof budgetVsSpentRows>[0]} */
    const budgets = [
      {
        category_id: 1,
        amount: "400.00",
        spent: "352.18",
        remaining: "47.82",
        status: "warning",
      },
    ];
    expect(budgetVsSpentRows(budgets, CATEGORY_NAMES)).toEqual([
      {
        categoryId: 1,
        categoryName: "Groceries",
        amount: "400.00",
        spent: "352.18",
        remaining: "47.82",
        status: "warning",
      },
    ]);
  });

  it("falls back to a placeholder name for an unknown category", () => {
    const budgets = [{ category_id: 99, amount: "100.00", spent: "0.00", remaining: "100.00" }];
    expect(budgetVsSpentRows(budgets, CATEGORY_NAMES)[0].categoryName).toBe("Unknown category");
  });
});

describe("currentMonthWindow", () => {
  it("spans the 1st of the month through the reference date, not month-end", () => {
    expect(currentMonthWindow(new Date(2026, 9, 15))).toEqual({
      periodStart: "2026-10-01",
      periodEnd: "2026-10-15",
    });
  });
});

describe("last30DaysWindow", () => {
  it("spans 30 inclusive calendar days ending on the reference date, crossing a month boundary", () => {
    expect(last30DaysWindow(new Date(2026, 2, 15))).toEqual({
      periodStart: "2026-02-14",
      periodEnd: "2026-03-15",
    });
  });
});

describe("spendingByCategory", () => {
  const window = { periodStart: "2026-10-01", periodEnd: "2026-10-31" };

  it("sums amounts grouped by category, within the window", () => {
    const expenses = [
      { category_id: 1, amount: "10.00", date: "2026-10-05" },
      { category_id: 1, amount: "5.50", date: "2026-10-10" },
      { category_id: 2, amount: "20.00", date: "2026-10-01" },
      { category_id: 1, amount: "999.00", date: "2026-09-30" }, // outside window
      { category_id: 1, amount: "999.00", date: "2026-11-01" }, // outside window
    ];
    expect(spendingByCategory(expenses, CATEGORY_NAMES, window)).toEqual([
      { categoryId: 2, categoryName: "Transport", total: "20.00" },
      { categoryId: 1, categoryName: "Groceries", total: "15.50" },
    ]);
  });

  it("includes the window's boundary dates", () => {
    const expenses = [
      { category_id: 1, amount: "1.00", date: window.periodStart },
      { category_id: 1, amount: "2.00", date: window.periodEnd },
    ];
    expect(spendingByCategory(expenses, CATEGORY_NAMES, window)).toEqual([
      { categoryId: 1, categoryName: "Groceries", total: "3.00" },
    ]);
  });

  it("omits categories with no matching expenses rather than zero-filling", () => {
    expect(spendingByCategory([], CATEGORY_NAMES, window)).toEqual([]);
  });
});

describe("dailyTotals", () => {
  it("zero-fills every day in the window, including no-spend days", () => {
    const window = { periodStart: "2026-10-01", periodEnd: "2026-10-03" };
    const expenses = [{ category_id: 1, amount: "10.00", date: "2026-10-01" }];
    expect(dailyTotals(expenses, window)).toEqual([
      { date: "2026-10-01", total: "10.00" },
      { date: "2026-10-02", total: "0" },
      { date: "2026-10-03", total: "0" },
    ]);
  });

  it("sums multiple expenses on the same day", () => {
    const window = { periodStart: "2026-10-01", periodEnd: "2026-10-01" };
    const expenses = [
      { category_id: 1, amount: "10.00", date: "2026-10-01" },
      { category_id: 2, amount: "5.00", date: "2026-10-01" },
    ];
    expect(dailyTotals(expenses, window)).toEqual([{ date: "2026-10-01", total: "15.00" }]);
  });

  it("returns results in chronological order across a month boundary", () => {
    const window = { periodStart: "2026-10-30", periodEnd: "2026-11-01" };
    expect(dailyTotals([], window).map((d) => d.date)).toEqual([
      "2026-10-30",
      "2026-10-31",
      "2026-11-01",
    ]);
  });
});

describe("toPlotNumber", () => {
  it("converts a decimal string to a plot-usable number", () => {
    expect(toPlotNumber("47.82")).toBe(47.82);
    expect(toPlotNumber("0")).toBe(0);
  });
});
