// Component tests for the edit-budget screen (#53).
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import { writable } from "svelte/store";

const gotoMock = vi.fn();
vi.mock("$app/navigation", () => ({
  goto: (...args) => gotoMock(...args),
}));

vi.mock("$app/stores", () => ({
  page: writable({ params: { id: "1" } }),
}));

import { page as pageStore } from "$app/stores";
import EditBudgetPage from "./+page.svelte";

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

function mockApi({ budgets = BUDGETS } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      if (String(url).includes("/api/categories/")) {
        return fakeResponse({
          status: 200,
          body: JSON.stringify({ categories: CATEGORIES }),
        });
      }
      return fakeResponse({ status: 200, body: JSON.stringify({ budgets }) });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  gotoMock.mockClear();
  pageStore.set({ params: { id: "1" } });
});

describe("edit budget page (#53)", () => {
  it("T-1: shows the category and month read-only, with an editable, pre-filled limit", async () => {
    mockApi();
    render(EditBudgetPage);

    expect(await screen.findByText("Alimentation")).toBeTruthy();
    expect(screen.getByText("2026-10")).toBeTruthy();
    expect(screen.queryByLabelText(/^category$/i)).toBeNull();
    expect(screen.queryByLabelText(/^month$/i)).toBeNull();

    const limit = screen.getByLabelText(/^limit$/i);
    expect(limit.value).toBe("200.00");
  });

  it("T-2: an id with no matching budget shows a not-found message instead of a form", async () => {
    mockApi({ budgets: [] });
    render(EditBudgetPage);

    expect(await screen.findByText(/couldn't be found/i)).toBeTruthy();
    expect(screen.queryByLabelText(/^limit$/i)).toBeNull();
  });

  it("T-3: submits a PATCH with only amount/alert_threshold and redirects on success", async () => {
    mockApi();
    render(EditBudgetPage);
    const limit = await screen.findByLabelText(/^limit$/i);

    await fireEvent.input(limit, { target: { value: "250.00" } });

    fetch.mockResolvedValueOnce(
      fakeResponse({ status: 200, body: JSON.stringify({ id: 1 }) }),
    );
    await fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    const patchCall = fetch.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(patchCall[0]).toBe("http://localhost:8000/api/budgets/1/");
    expect(JSON.parse(patchCall[1].body)).toEqual({
      amount: "250.00",
      alert_threshold: "80.00",
    });

    await vi.waitFor(() => expect(gotoMock).toHaveBeenCalledWith("/budgets"));
  });
});
