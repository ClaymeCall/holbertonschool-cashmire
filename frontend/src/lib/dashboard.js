// Pure aggregation helpers for the landing-page dashboard charts. No fetch,
// no Svelte, no D3 — just turning Budget/Expense/Category lists (as returned
// by $lib/api/*) into the shapes the chart components render. Keeping this
// framework-free makes it trivially unit-testable with plain fixtures.
import { sumDecimal, compareDecimal } from "./money.js";

/**
 * @typedef {Object} BudgetVsSpentRow
 * @property {number} categoryId
 * @property {string} categoryName
 * @property {string} amount
 * @property {string} spent
 * @property {string} remaining
 * @property {"ok" | "warning" | "full" | "exceeded" | undefined} status
 */

/**
 * One row per budget — budgets are already one-per-category-per-period, so
 * this is a map, not an aggregation. `spent`/`remaining`/`status` are
 * server-computed (`docs/decisions/budget-thresholds.md`); never recompute
 * them here.
 *
 * @param {Pick<import("./api/budgets").Budget, "category_id" | "amount" | "spent" | "remaining" | "status">[]} budgets
 * @param {Map<number, string>} categoryNames
 * @returns {BudgetVsSpentRow[]}
 */
export function budgetVsSpentRows(budgets, categoryNames) {
  return budgets.map((budget) => ({
    categoryId: budget.category_id,
    categoryName: categoryNames.get(budget.category_id) ?? "Unknown category",
    amount: budget.amount,
    spent: budget.spent,
    remaining: budget.remaining,
    status: budget.status,
  }));
}

/**
 * @typedef {Object} DateWindow
 * @property {string} periodStart `"YYYY-MM-DD"`, inclusive.
 * @property {string} periodEnd `"YYYY-MM-DD"`, inclusive.
 */

/**
 * @param {number} n
 * @returns {string} zero-padded to 2 digits.
 */
function pad2(n) {
  return String(n).padStart(2, "0");
}

/**
 * `"YYYY-MM-DD"` from a Date's *local* calendar fields — never
 * `toISOString().slice(0, 10)`, which reads UTC fields and can land on the
 * wrong calendar day near local midnight.
 *
 * @param {Date} date
 * @returns {string}
 */
function toLocalDateString(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

/**
 * The 1st of `referenceDate`'s local calendar month through `referenceDate`
 * itself — NOT the month's last day, since there's no future expense data to
 * show.
 *
 * @param {Date} [referenceDate] injectable so tests can assert exact bounds
 *   without faking the system clock.
 * @returns {DateWindow}
 */
export function currentMonthWindow(referenceDate = new Date()) {
  const periodStart = `${referenceDate.getFullYear()}-${pad2(referenceDate.getMonth() + 1)}-01`;
  return { periodStart, periodEnd: toLocalDateString(referenceDate) };
}

/**
 * 30 local calendar days ending on `referenceDate`, inclusive of both ends.
 *
 * @param {Date} [referenceDate]
 * @returns {DateWindow}
 */
export function last30DaysWindow(referenceDate = new Date()) {
  const start = new Date(referenceDate);
  start.setDate(start.getDate() - 29);
  return { periodStart: toLocalDateString(start), periodEnd: toLocalDateString(referenceDate) };
}

/**
 * @param {string} date `"YYYY-MM-DD"`.
 * @param {DateWindow} window
 * @returns {boolean}
 */
function isInWindow(date, window) {
  // Fixed-width "YYYY-MM-DD" strings compare correctly lexicographically —
  // this is calendar-date containment, not money, so plain `<=` is fine here.
  return date >= window.periodStart && date <= window.periodEnd;
}

/**
 * @typedef {Object} CategoryTotal
 * @property {number} categoryId
 * @property {string} categoryName
 * @property {string} total
 */

/**
 * Sums `expense.amount` grouped by `category_id`, restricted to `window`.
 * Categories with no matching expenses are omitted (not zero-filled) —
 * unlike {@link dailyTotals}, a pie chart has no use for an empty slice.
 *
 * @param {Pick<import("./api/expenses").Expense, "category_id" | "amount" | "date">[]} expenses
 * @param {Map<number, string>} categoryNames
 * @param {DateWindow} window
 * @returns {CategoryTotal[]} sorted by total descending, ties broken by
 *   `categoryId` ascending for deterministic output.
 */
export function spendingByCategory(expenses, categoryNames, window) {
  /** @type {Map<number, string[]>} */
  const amountsByCategory = new Map();
  for (const expense of expenses) {
    if (!isInWindow(expense.date, window)) continue;
    const amounts = amountsByCategory.get(expense.category_id) ?? [];
    amounts.push(expense.amount);
    amountsByCategory.set(expense.category_id, amounts);
  }

  const totals = Array.from(amountsByCategory, ([categoryId, amounts]) => ({
    categoryId,
    categoryName: categoryNames.get(categoryId) ?? "Unknown category",
    total: sumDecimal(amounts),
  }));

  totals.sort((a, b) => compareDecimal(b.total, a.total) || a.categoryId - b.categoryId);
  return totals;
}

/**
 * @typedef {Object} DailyTotal
 * @property {string} date `"YYYY-MM-DD"`.
 * @property {string} total
 */

/**
 * Sums `expense.amount` per calendar day across `window`, zero-filled for
 * every day in range — a trend line with gaps on no-spend days reads as
 * missing data, not "nothing spent".
 *
 * @param {Pick<import("./api/expenses").Expense, "amount" | "date">[]} expenses
 * @param {DateWindow} window
 * @returns {DailyTotal[]} chronological.
 */
export function dailyTotals(expenses, window) {
  /** @type {Map<string, string[]>} */
  const amountsByDate = new Map();
  for (const expense of expenses) {
    if (!isInWindow(expense.date, window)) continue;
    const amounts = amountsByDate.get(expense.date) ?? [];
    amounts.push(expense.amount);
    amountsByDate.set(expense.date, amounts);
  }

  const [startYear, startMonth, startDay] = window.periodStart.split("-").map(Number);
  const cursor = new Date(startYear, startMonth - 1, startDay);
  const results = [];
  while (toLocalDateString(cursor) <= window.periodEnd) {
    const date = toLocalDateString(cursor);
    results.push({ date, total: sumDecimal(amountsByDate.get(date) ?? []) });
    cursor.setDate(cursor.getDate() + 1);
  }
  return results;
}

/**
 * The one narrow, explicit exception to this app's ban on coercing money
 * strings to JS numbers (see `money.js`'s file-top comment) — scoped to
 * this file, not `money.js`, so `money.test.js`'s source-text scan stays
 * untouched. For D3/LayerChart scale and pixel math ONLY: never use the
 * result for comparisons or further arithmetic, both of which stay in
 * `money.js`'s decimal-string functions.
 *
 * @param {string} decimalString
 * @returns {number}
 */
export function toPlotNumber(decimalString) {
  return Number(decimalString);
}
