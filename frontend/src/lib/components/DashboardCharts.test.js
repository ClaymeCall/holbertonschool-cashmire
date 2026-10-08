// Guards the centralized-fetch design DashboardCharts exists for (see its
// file-top comment): each of categories/expenses/budgets must be fetched
// exactly once, not once per chart.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/svelte";

import DashboardCharts from "./DashboardCharts.svelte";

const CATEGORIES = [{ id: 5, name: "Groceries" }];
const EXPENSES = [{ id: 1, category_id: 5, amount: "10.00", description: null, date: "2026-10-01" }];
const BUDGETS = [
  {
    id: 1,
    category_id: 5,
    amount: "200.00",
    period_start: "2026-10-01",
    period_end: "2026-10-31",
    alert_threshold: "80.00",
    spent: "10.00",
    remaining: "190.00",
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
  const fetchMock = vi.fn(async (url) => {
    const u = String(url);
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
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("DashboardCharts", () => {
  it("fetches categories/expenses/budgets exactly once and renders all 3 charts", async () => {
    const fetchMock = mockApi();
    render(DashboardCharts);

    expect(await screen.findByRole("heading", { name: /budget vs dépenses/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /cette période/i })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /30 derniers jours/i })).toBeTruthy();

    const calledUrls = fetchMock.mock.calls.map(([url]) => String(url));
    expect(calledUrls.filter((u) => u.includes("/api/categories/"))).toHaveLength(1);
    expect(calledUrls.filter((u) => u.includes("/api/expenses/"))).toHaveLength(1);
    expect(calledUrls.filter((u) => u.includes("/api/budgets/"))).toHaveLength(1);
  });

  it("shows an error with a working retry on fetch failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(DashboardCharts);

    expect(await screen.findByRole("alert")).toBeTruthy();
    const retry = screen.getByRole("button", { name: /réessayer/i });

    mockApi();
    retry.click();
    expect(await screen.findByRole("heading", { name: /budget vs dépenses/i })).toBeTruthy();
  });
});
