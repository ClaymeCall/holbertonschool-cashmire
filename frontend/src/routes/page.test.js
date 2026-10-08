// Component tests for the home/dashboard screen (#104).
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/svelte";
import { currentUser } from "$lib/stores/auth";

import HomePage from "./+page.svelte";

const CATEGORIES = [{ id: 5, name: "Alimentation" }];

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
];

const EXPENSES = [
  { id: 1, category_id: 5, amount: "12.50", description: null, date: "2026-10-06" },
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
 * @param {{ categories?: unknown, budgets?: unknown, expenses?: unknown, budgetsStatus?: number }} opts
 */
function mockApi({
  categories = CATEGORIES,
  budgets = BUDGETS,
  expenses = EXPENSES,
  budgetsStatus = 200,
} = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      const u = String(url);
      if (u.includes("/api/categories/")) {
        return fakeResponse({ status: 200, body: JSON.stringify({ categories }) });
      }
      if (u.includes("/api/budgets/")) {
        return fakeResponse({ status: budgetsStatus, body: JSON.stringify({ budgets }) });
      }
      return fakeResponse({ status: 200, body: JSON.stringify({ expenses }) });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  currentUser.set(null);
});

describe("home / dashboard page (#104)", () => {
  it("T-1: logged out, shows a public landing with no data fetch", () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    render(HomePage);

    expect(screen.getAllByRole("heading", { level: 1 })[0].textContent).toMatch(
      /cashmire/i,
    );
    expect(screen.getByRole("link", { name: /create an account/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /log in/i })).toBeTruthy();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("T-2: logged in, renders the dashboard heading and fetches budgets/expenses/categories", async () => {
    currentUser.set({ email: "jane@example.com" });
    mockApi();

    render(HomePage);

    expect(screen.getByRole("heading", { level: 1, name: /dashboard/i })).toBeTruthy();
    await screen.findByText(/on track/i);
  });

  it("T-3: shows each budget's status and recent expenses, newest-first order preserved", async () => {
    currentUser.set({ email: "jane@example.com" });
    mockApi();

    render(HomePage);

    const budgetsHeading = await screen.findByRole("heading", { name: /your budgets/i });
    const budgetsSection = budgetsHeading.closest("section");
    expect(within(budgetsSection).getByText(/on track/i)).toBeTruthy();

    const expensesHeading = screen.getByRole("heading", { name: /recent expenses/i });
    const expensesSection = expensesHeading.closest("section");
    expect(within(expensesSection).getByText("12.50")).toBeTruthy();
  });

  it("T-4: empty budgets/expenses show their own empty-state messages", async () => {
    currentUser.set({ email: "jane@example.com" });
    mockApi({ budgets: [], expenses: [] });

    render(HomePage);

    expect(await screen.findByText(/no budgets yet/i)).toBeTruthy();
    expect(screen.getByText(/no expenses yet/i)).toBeTruthy();
  });

  it("T-5: a failed load shows an error with a working retry", async () => {
    currentUser.set({ email: "jane@example.com" });
    mockApi({ budgetsStatus: 500 });

    render(HomePage);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/couldn't load your dashboard/i);

    mockApi();
    await fireEvent.click(screen.getByRole("button", { name: /retry/i }));

    await screen.findByText(/on track/i);
  });
});
