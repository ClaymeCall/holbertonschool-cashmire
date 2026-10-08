// Component tests for the create-expense screen (#41).
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";

const gotoMock = vi.fn();
vi.mock("$app/navigation", () => ({
  goto: (...args) => gotoMock(...args),
}));

import NewExpensePage from "./+page.svelte";

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

describe("create expense page (#41)", () => {
  it("T-1: loads categories and renders the form with an amount, date, category and description field", async () => {
    mockCategoriesFetch();
    render(NewExpensePage);

    expect(await screen.findByLabelText(/^amount$/i)).toBeTruthy();
    expect(screen.getByLabelText(/^date$/i)).toBeTruthy();
    expect(screen.getByLabelText(/^category$/i)).toBeTruthy();
    expect(screen.getByLabelText(/^description$/i)).toBeTruthy();
  });

  it("T-2: a non-positive amount shows a client-side error and makes no create request", async () => {
    mockCategoriesFetch();
    render(NewExpensePage);
    await screen.findByLabelText(/^amount$/i);

    await fireEvent.input(screen.getByLabelText(/^amount$/i), {
      target: { value: "0" },
    });
    await fireEvent.click(screen.getByRole("button", { name: /add expense/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/greater than 0/i);
    expect(fetch).toHaveBeenCalledTimes(1); // only the categories GET
  });

  it("T-3: submits the amount as a string and redirects to the expense list on success", async () => {
    mockCategoriesFetch();
    render(NewExpensePage);
    await screen.findByLabelText(/^amount$/i);

    await fireEvent.input(screen.getByLabelText(/^amount$/i), {
      target: { value: "12.50" },
    });
    await fireEvent.input(screen.getByLabelText(/^date$/i), {
      target: { value: "2026-10-06" },
    });
    await fireEvent.input(screen.getByLabelText(/^description$/i), {
      target: { value: "Market" },
    });

    fetch.mockResolvedValueOnce(
      fakeResponse({ status: 201, body: JSON.stringify({ id: 9 }) }),
    );
    await fireEvent.click(screen.getByRole("button", { name: /add expense/i }));

    const [, createInit] = fetch.mock.calls[1];
    const body = JSON.parse(createInit.body);
    expect(body).toEqual({
      category_id: 5,
      amount: "12.50",
      description: "Market",
      date: "2026-10-06",
    });

    await vi.waitFor(() => expect(gotoMock).toHaveBeenCalledWith("/expenses"));
  });

  it("T-4: a 400 response surfaces the backend's field errors", async () => {
    mockCategoriesFetch();
    render(NewExpensePage);
    await screen.findByLabelText(/^amount$/i);

    await fireEvent.input(screen.getByLabelText(/^amount$/i), {
      target: { value: "12.50" },
    });
    await fireEvent.input(screen.getByLabelText(/^date$/i), {
      target: { value: "2026-10-06" },
    });

    fetch.mockResolvedValueOnce(
      fakeResponse({
        status: 400,
        body: JSON.stringify({ amount: ["Doit être > 0"] }),
      }),
    );
    await fireEvent.click(screen.getByRole("button", { name: /add expense/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/doit être > 0/i);
    expect(gotoMock).not.toHaveBeenCalled();
  });
});
