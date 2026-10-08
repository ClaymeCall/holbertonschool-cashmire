// Component tests for the landing page (issue #104 componentization
// follow-up): the health-status line it always had, plus the logged-in-only
// expenses/budgets previews that prove ExpensesList/BudgetsList
// (lib/components/) are genuinely reusable outside their own routes.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/svelte";

import { setCurrentUser } from "$lib/auth.svelte.js";
import HomePage from "./+page.svelte";

const CATEGORIES = [
  { id: 5, name: "Alimentation" },
  { id: 7, name: "Transport" },
];

const EXPENSES = [
  { id: 1, category_id: 5, amount: "10.00", description: null, date: "2026-10-01" },
  { id: 2, category_id: 5, amount: "20.00", description: null, date: "2026-10-02" },
  { id: 3, category_id: 5, amount: "30.00", description: null, date: "2026-10-03" },
  { id: 4, category_id: 5, amount: "40.00", description: null, date: "2026-10-04" },
];

const BUDGETS = [
  {
    id: 1,
    category_id: 5,
    amount: "200.00",
    period_start: "2026-10-01",
    period_end: "2026-10-31",
    alert_threshold: "80.00",
    spent: "45.00",
    remaining: "155.00",
    status: "ok",
  },
  {
    id: 2,
    category_id: 7,
    amount: "100.00",
    period_start: "2026-10-01",
    period_end: "2026-10-31",
    alert_threshold: "80.00",
    spent: "20.00",
    remaining: "80.00",
    status: "ok",
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

function mockApi() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      const u = String(url);
      if (u.includes("/api/health/")) {
        return fakeResponse({ status: 200, body: JSON.stringify({ status: "ok" }) });
      }
      if (u.includes("/api/categories/")) {
        return fakeResponse({ status: 200, body: JSON.stringify({ categories: CATEGORIES }) });
      }
      if (u.includes("/api/expenses/")) {
        return fakeResponse({ status: 200, body: JSON.stringify({ expenses: EXPENSES }) });
      }
      if (u.includes("/api/budgets/")) {
        return fakeResponse({ status: 200, body: JSON.stringify({ budgets: BUDGETS }) });
      }
      throw new Error(`Unexpected fetch to ${u}`);
    }),
  );
}

describe("landing page (#104 componentization follow-up)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    setCurrentUser(null);
  });

  it("while anonymous, shows the API status but no dashboard or expenses/budgets previews", async () => {
    mockApi();
    render(HomePage);

    expect(await screen.findByText("ok")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: /spending at a glance/i })).toBeNull();
    expect(screen.queryByRole("heading", { name: /recent expenses/i })).toBeNull();
    expect(screen.queryByRole("heading", { name: /your budgets/i })).toBeNull();
  });

  it("while logged in, shows the dashboard charts above the expenses/budgets previews", async () => {
    setCurrentUser({ id: 1, email: "demo@example.com" });
    mockApi();
    render(HomePage);

    const dashboardHeading = await screen.findByRole("heading", {
      name: /spending at a glance/i,
    });
    const expensesHeading = await screen.findByRole("heading", { name: /recent expenses/i });
    expect(await screen.findByRole("heading", { name: /budget vs spent/i })).toBeTruthy();
    expect(await screen.findByRole("heading", { name: /spending by category/i })).toBeTruthy();
    expect(await screen.findByRole("heading", { name: /last 30 days/i })).toBeTruthy();
    // DOM order: dashboard comes before the pre-existing previews.
    expect(
      dashboardHeading.compareDocumentPosition(expensesHeading) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("while logged in, previews the 3 most recent expenses with a link to the full list", async () => {
    setCurrentUser({ id: 1, email: "demo@example.com" });
    mockApi();
    render(HomePage);

    const heading = await screen.findByRole("heading", { name: /recent expenses/i });
    const section = /** @type {HTMLElement} */ (heading.closest("section"));
    expect(await within(section).findAllByRole("listitem")).toHaveLength(3);
    expect(
      within(section).getByRole("link", { name: /view all/i }).getAttribute("href"),
    ).toBe("/expenses");
  });

  it("while logged in, previews the budgets dashboard with a link to the full list", async () => {
    setCurrentUser({ id: 1, email: "demo@example.com" });
    mockApi();
    render(HomePage);

    const heading = await screen.findByRole("heading", { name: /your budgets/i });
    const section = /** @type {HTMLElement} */ (heading.closest("section"));
    expect(await within(section).findAllByRole("listitem")).toHaveLength(2);
    expect(within(section).getByText("Alimentation")).toBeTruthy();
    expect(
      within(section).getByRole("link", { name: /view all/i }).getAttribute("href"),
    ).toBe("/budgets");
  });
});
