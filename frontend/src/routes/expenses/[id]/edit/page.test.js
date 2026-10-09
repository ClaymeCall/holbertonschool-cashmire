// Component tests for the edit-expense screen (#41).
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
import EditExpensePage from "./+page.svelte";

const CATEGORIES = [
  { id: 5, name: "Alimentation" },
  { id: 7, name: "Transport" },
];

const EXPENSES = [
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

function mockApi({ expenses = EXPENSES } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      if (String(url).includes("/api/categories/")) {
        return fakeResponse({
          status: 200,
          body: JSON.stringify({ categories: CATEGORIES }),
        });
      }
      return fakeResponse({
        status: 200,
        body: JSON.stringify({ expenses }),
      });
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  gotoMock.mockClear();
  pageStore.set({ params: { id: "1" } });
});

describe("edit expense page (#41)", () => {
  it("T-1: pre-fills the form with the matching expense's current values", async () => {
    mockApi();
    render(EditExpensePage);

    const amount = await screen.findByLabelText(/^montant$/i);
    expect(amount.value).toBe("25.50");
    expect(screen.getByLabelText(/^date$/i).value).toBe("2026-10-05");
    expect(screen.getByLabelText(/^description$/i).value).toBe("Déjeuner");
    expect(screen.getByLabelText(/^catégorie$/i).value).toBe("5");
  });

  it("T-2: an id with no matching expense shows a not-found message instead of a form", async () => {
    mockApi({ expenses: [] });
    render(EditExpensePage);

    expect(await screen.findByText(/introuvable/i)).toBeTruthy();
    expect(screen.queryByLabelText(/^montant$/i)).toBeNull();
  });

  it("T-3: submits a PATCH with the edited fields and redirects to the expense list", async () => {
    mockApi();
    render(EditExpensePage);
    const amount = await screen.findByLabelText(/^montant$/i);

    await fireEvent.input(amount, { target: { value: "30.00" } });

    fetch.mockResolvedValueOnce(
      fakeResponse({ status: 200, body: JSON.stringify({ id: 1 }) }),
    );
    await fireEvent.click(screen.getByRole("button", { name: /enregistrer les modifications/i }));

    const patchCall = fetch.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(patchCall[0]).toBe("http://localhost:8000/api/expenses/1/");
    expect(JSON.parse(patchCall[1].body)).toEqual({
      category_id: 5,
      amount: "30.00",
      description: "Déjeuner",
      date: "2026-10-05",
    });

    await vi.waitFor(() => expect(gotoMock).toHaveBeenCalledWith("/expenses"));
  });
});
