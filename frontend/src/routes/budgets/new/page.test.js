// Component tests for the create-budget screen (#53).
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";

const gotoMock = vi.fn();
vi.mock("$app/navigation", () => ({
  goto: (...args) => gotoMock(...args),
}));

import NewBudgetPage from "./+page.svelte";

const CATEGORIES = [
  { id: 5, name: "Alimentation" },
  { id: 7, name: "Transport" },
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

function mockCategoriesFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      fakeResponse({
        status: 200,
        body: JSON.stringify({ categories: CATEGORIES }),
      }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  gotoMock.mockClear();
});

describe("create budget page (#53)", () => {
  it("T-1: renders a category select, a month field and an amount field", async () => {
    mockCategoriesFetch();
    render(NewBudgetPage);

    expect(await screen.findByLabelText(/^catégorie$/i)).toBeTruthy();
    expect(screen.getByLabelText(/^mois$/i)).toBeTruthy();
    expect(screen.getByLabelText(/^limite$/i)).toBeTruthy();
  });

  it("T-2: a non-positive limit shows a client-side error and makes no create request", async () => {
    mockCategoriesFetch();
    render(NewBudgetPage);
    await screen.findByLabelText(/^limite$/i);

    await fireEvent.input(screen.getByLabelText(/^limite$/i), {
      target: { value: "0" },
    });
    await fireEvent.click(screen.getByRole("button", { name: /ajouter un budget/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/supérieure à 0/i);
    expect(fetch).toHaveBeenCalledTimes(1); // only the categories GET
  });

  it("T-3: translates the chosen month into period_start/period_end and redirects on success", async () => {
    mockCategoriesFetch();
    render(NewBudgetPage);
    await screen.findByLabelText(/^limite$/i);

    await fireEvent.input(screen.getByLabelText(/^mois$/i), {
      target: { value: "2026-10" },
    });
    await fireEvent.input(screen.getByLabelText(/^limite$/i), {
      target: { value: "200.00" },
    });

    fetch.mockResolvedValueOnce(
      fakeResponse({ status: 201, body: JSON.stringify({ id: 1 }) }),
    );
    await fireEvent.click(screen.getByRole("button", { name: /ajouter un budget/i }));

    const [, createInit] = fetch.mock.calls[1];
    const body = JSON.parse(createInit.body);
    expect(body).toEqual({
      category_id: 5,
      amount: "200.00",
      period_start: "2026-10-01",
      period_end: "2026-10-31",
      alert_threshold: "80.00",
    });

    await vi.waitFor(() => expect(gotoMock).toHaveBeenCalledWith("/budgets"));
  });

  it("T-4: a 409 conflict shows the duplicate-budget message, not a generic failure", async () => {
    mockCategoriesFetch();
    render(NewBudgetPage);
    await screen.findByLabelText(/^limite$/i);

    await fireEvent.input(screen.getByLabelText(/^mois$/i), {
      target: { value: "2026-10" },
    });
    await fireEvent.input(screen.getByLabelText(/^limite$/i), {
      target: { value: "200.00" },
    });

    fetch.mockResolvedValueOnce(
      fakeResponse({
        status: 409,
        body: JSON.stringify({
          error: "CONFLICT",
          message: "Budget déjà existant pour cette période et catégorie",
        }),
      }),
    );
    await fireEvent.click(screen.getByRole("button", { name: /ajouter un budget/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/déjà existant/i);
    expect(gotoMock).not.toHaveBeenCalled();
  });

  it("T-5: a 403 response is reported as a rejected request, not missing authentication", async () => {
    mockCategoriesFetch();
    render(NewBudgetPage);
    await screen.findByLabelText(/^limit$/i);

    await fireEvent.input(screen.getByLabelText(/^month$/i), {
      target: { value: "2026-10" },
    });
    await fireEvent.input(screen.getByLabelText(/^limit$/i), {
      target: { value: "200.00" },
    });
    fetch.mockResolvedValueOnce(fakeResponse({ status: 403 }));
    await fireEvent.click(screen.getByRole("button", { name: /add budget/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/couldn't be verified/i);
    expect(alert.textContent).not.toMatch(/logged in/i);
  });

  it("T-6: a 401 response explains that an authenticated session is required", async () => {
    mockCategoriesFetch();
    render(NewBudgetPage);
    await screen.findByLabelText(/^limit$/i);

    await fireEvent.input(screen.getByLabelText(/^month$/i), {
      target: { value: "2026-10" },
    });
    await fireEvent.input(screen.getByLabelText(/^limit$/i), {
      target: { value: "200.00" },
    });
    fetch.mockResolvedValueOnce(fakeResponse({ status: 401 }));
    await fireEvent.click(screen.getByRole("button", { name: /add budget/i }));

    expect((await screen.findByRole("alert")).textContent).toMatch(/logged in/i);
  });
});
