// Component tests for the expense list screen (#40). Same conventions as
// ../login/page.test.js: no @testing-library/jest-dom, `fetch` always
// stubbed so no test makes a real network request.
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/svelte";

import ExpensesPage from "./+page.svelte";

const CATEGORIES = [
  { id: 5, name: "Alimentation" },
  { id: 7, name: "Transport" },
];

const EXPENSES = [
  {
    id: 2,
    category_id: 7,
    amount: "5.00",
    description: null,
    date: "2026-10-06",
  },
  {
    id: 1,
    category_id: 5,
    amount: "25.50",
    description: "Déjeuner",
    date: "2026-10-05",
  },
];

/**
 * @param {{ status: number, body?: string }} opts
 */
function fakeResponse({ status, body = "" }) {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: () => Promise.resolve(body),
  };
}

/**
 * @param {{ categories?: unknown, expenses?: unknown, categoriesStatus?: number, expensesStatus?: number }} opts
 */
function mockApi({
  categories = CATEGORIES,
  expenses = EXPENSES,
  categoriesStatus = 200,
  expensesStatus = 200,
} = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      if (String(url).includes("/api/categories/")) {
        return fakeResponse({
          status: categoriesStatus,
          body: JSON.stringify({ categories }),
        });
      }
      if (String(url).includes("/api/expenses/")) {
        return fakeResponse({
          status: expensesStatus,
          body: JSON.stringify({ expenses }),
        });
      }
      throw new Error(`Unexpected fetch to ${url}`);
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("expense list page (#40)", () => {
  it("T-1: exposes exactly one level-1 heading and a link to add an expense", async () => {
    mockApi();
    render(ExpensesPage);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(
      screen.getByRole("link", { name: /add expense/i }).getAttribute("href"),
    ).toBe("/expenses/new");
  });

  it("T-2: renders each expense with its formatted amount, category name, and an edit link", async () => {
    mockApi();
    render(ExpensesPage);

    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(2);

    expect(within(items[0]).getByText("5.00")).toBeTruthy();
    expect(within(items[0]).getByText("Transport")).toBeTruthy();
    expect(
      within(items[0]).getByRole("link", { name: /edit/i }).getAttribute("href"),
    ).toBe("/expenses/2/edit");

    expect(within(items[1]).getByText("25.50")).toBeTruthy();
    expect(within(items[1]).getByText("Alimentation")).toBeTruthy();
    expect(within(items[1]).getByText("Déjeuner")).toBeTruthy();
  });

  it("T-3: shows an empty-state message and no list when there are no expenses", async () => {
    mockApi({ expenses: [] });
    render(ExpensesPage);

    expect(await screen.findByText(/no expenses yet/i)).toBeTruthy();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("T-4: a failed load shows an error with a working retry", async () => {
    mockApi({ expensesStatus: 500 });
    render(ExpensesPage);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/couldn't load your expenses/i);

    mockApi();
    await fireEvent.click(screen.getByRole("button", { name: /retry/i }));

    expect(await screen.findAllByRole("listitem")).toHaveLength(2);
  });
});
