// Unit tests for the budgets API client (#52/#53). Same conventions as
// ./expenses.test.js: stubbed `globalThis.fetch`, no live server.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { API_BASE_URL } from "$lib/api";
import {
  listBudgets,
  createBudget,
  updateBudget,
  monthToPeriod,
  periodToMonth,
} from "./budgets.js";

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

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("listBudgets", () => {
  it("GETs the collection and returns the `budgets` array", async () => {
    const budgets = [{ id: 1, amount: "500.00" }];
    fetch.mockResolvedValue(
      fakeResponse({ status: 200, body: JSON.stringify({ budgets }) }),
    );
    await expect(listBudgets()).resolves.toEqual(budgets);
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/budgets/`);
    expect(init.credentials).toBe("include");
  });

  it("encodes category_id as a query param when given", async () => {
    fetch.mockResolvedValue(
      fakeResponse({ status: 200, body: JSON.stringify({ budgets: [] }) }),
    );
    await listBudgets({ category_id: 5 });
    const [url] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/budgets/?category_id=5`);
  });
});

describe("createBudget", () => {
  it("POSTs the given fields, with amount/alert_threshold as strings", async () => {
    fetch.mockResolvedValue(
      fakeResponse({ status: 201, body: JSON.stringify({ id: 1 }) }),
    );
    await createBudget({
      category_id: 5,
      amount: "500.00",
      period_start: "2026-10-01",
      period_end: "2026-10-31",
      alert_threshold: "80.00",
    });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/budgets/`);
    expect(init.method).toBe("POST");
    const body = JSON.parse(init.body);
    expect(typeof body.amount).toBe("string");
    expect(body.period_start).toBe("2026-10-01");
  });
});

describe("updateBudget", () => {
  it("PATCHes only amount/alert_threshold", async () => {
    fetch.mockResolvedValue(
      fakeResponse({ status: 200, body: JSON.stringify({ id: 1 }) }),
    );
    await updateBudget(1, { amount: "600.00" });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/budgets/1/`);
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ amount: "600.00" });
  });
});

describe("monthToPeriod", () => {
  it("resolves a 31-day month's last day correctly", () => {
    expect(monthToPeriod("2026-10")).toEqual({
      period_start: "2026-10-01",
      period_end: "2026-10-31",
    });
  });

  it("resolves February in a leap year to the 29th", () => {
    expect(monthToPeriod("2028-02")).toEqual({
      period_start: "2028-02-01",
      period_end: "2028-02-29",
    });
  });

  it("resolves February in a non-leap year to the 28th", () => {
    expect(monthToPeriod("2026-02")).toEqual({
      period_start: "2026-02-01",
      period_end: "2026-02-28",
    });
  });
});

describe("periodToMonth", () => {
  it("is the inverse of monthToPeriod's period_start", () => {
    expect(periodToMonth("2026-10-01")).toBe("2026-10");
  });
});
