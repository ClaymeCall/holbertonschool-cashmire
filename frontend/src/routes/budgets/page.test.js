// Component tests for the budget dashboard screen (#52).
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/svelte";

import BudgetsPage from "./+page.svelte";

const CATEGORIES = [
  { id: 5, name: "Alimentation" },
  { id: 7, name: "Transport" },
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
    spent: "120.00",
    remaining: "-20.00",
    status: "exceeded",
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
 * @param {{ categories?: unknown, budgets?: unknown, budgetsStatus?: number }} opts
 */
function mockApi({
  categories = CATEGORIES,
  budgets = BUDGETS,
  budgetsStatus = 200,
} = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      if (String(url).includes("/api/categories/")) {
        return fakeResponse({
          status: 200,
          body: JSON.stringify({ categories }),
        });
      }
      return fakeResponse({
        status: budgetsStatus,
        body: JSON.stringify({ budgets }),
      });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("budget dashboard page (#52)", () => {
  it("T-1: renders each budget's category, spent/remaining amounts and status label", async () => {
    mockApi();
    render(BudgetsPage);

    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(2);

    expect(within(items[0]).getByText("Alimentation")).toBeTruthy();
    expect(within(items[0]).getByText(/45\.00 spent of 200\.00/)).toBeTruthy();
    expect(within(items[0]).getByText(/on track/i)).toBeTruthy();

    expect(within(items[1]).getByText("Transport")).toBeTruthy();
    expect(within(items[1]).getByText(/over budget/i)).toBeTruthy();
  });

  it("T-2: the progress bar is an accessible progressbar with a value capped at 100", async () => {
    mockApi();
    render(BudgetsPage);
    const items = await screen.findAllByRole("listitem");

    const okBar = within(items[0]).getByRole("progressbar");
    expect(okBar.getAttribute("aria-valuenow")).toBe("22.5");

    // Spent (120) > amount (100): the bar caps at 100, the "Over budget"
    // text label is what communicates the overspend, not the bar's width.
    const exceededBar = within(items[1]).getByRole("progressbar");
    expect(exceededBar.getAttribute("aria-valuenow")).toBe("100");
  });

  it("T-2b: shows the consumed percentage as visible text, uncapped when over budget", async () => {
    mockApi();
    render(BudgetsPage);
    const items = await screen.findAllByRole("listitem");

    expect(within(items[0]).getByText("22.5% used")).toBeTruthy();
    expect(within(items[1]).getByText("120.0% used")).toBeTruthy();
  });

  it("T-3: shows an empty-state message explaining how to create a budget when there are none", async () => {
    mockApi({ budgets: [] });
    render(BudgetsPage);

    expect(await screen.findByText(/no budgets yet/i)).toBeTruthy();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("T-4: a failed load shows an error with a working retry", async () => {
    mockApi({ budgetsStatus: 500 });
    render(BudgetsPage);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/couldn't load your budgets/i);

    mockApi();
    await fireEvent.click(screen.getByRole("button", { name: /retry/i }));

    expect(await screen.findAllByRole("listitem")).toHaveLength(2);
  });
});
