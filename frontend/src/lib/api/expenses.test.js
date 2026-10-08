// Unit tests for the expenses API client (#40/#41). Pure unit tests with a
// stubbed `globalThis.fetch`, same conventions as `../api.test.js`.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { API_BASE_URL } from "$lib/api";
import { listExpenses, createExpense, updateExpense } from "./expenses.js";

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

describe("listExpenses", () => {
  it("fetches the plain collection with no query string when no filters are given", async () => {
    fetch.mockResolvedValue(
      fakeResponse({ status: 200, body: JSON.stringify({ expenses: [] }) }),
    );
    await listExpenses();
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/expenses/`);
    expect(init.credentials).toBe("include");
  });

  it("encodes category_id/date_from/date_to as query params and omits unset ones", async () => {
    fetch.mockResolvedValue(
      fakeResponse({ status: 200, body: JSON.stringify({ expenses: [] }) }),
    );
    await listExpenses({ category_id: 5, date_from: "2026-10-01" });
    const [url] = fetch.mock.calls[0];
    expect(url).toBe(
      `${API_BASE_URL}/api/expenses/?category_id=5&date_from=2026-10-01`,
    );
  });

  it("returns the `expenses` array from the response envelope", async () => {
    const expenses = [{ id: 1, amount: "25.50" }];
    fetch.mockResolvedValue(
      fakeResponse({ status: 200, body: JSON.stringify({ expenses }) }),
    );
    await expect(listExpenses()).resolves.toEqual(expenses);
  });
});

describe("createExpense", () => {
  it("POSTs the given fields as JSON, with the amount sent as a string", async () => {
    fetch.mockResolvedValue(
      fakeResponse({ status: 201, body: JSON.stringify({ id: 1 }) }),
    );
    await createExpense({
      category_id: 5,
      amount: "25.50",
      description: "Lunch",
      date: "2026-10-06",
    });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/expenses/`);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    const body = JSON.parse(init.body);
    expect(body.amount).toBe("25.50");
    expect(typeof body.amount).toBe("string");
  });
});

describe("updateExpense", () => {
  it("PATCHes the expense's detail route with the given fields", async () => {
    fetch.mockResolvedValue(
      fakeResponse({ status: 200, body: JSON.stringify({ id: 7 }) }),
    );
    await updateExpense(7, { amount: "30.00" });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/expenses/7/`);
    expect(init.method).toBe("PATCH");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({ amount: "30.00" });
  });
});
