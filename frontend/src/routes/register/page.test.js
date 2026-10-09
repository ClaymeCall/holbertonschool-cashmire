// Component tests for the registration screen (#28).
//
// Same conventions as frontend/src/routes/health/page.test.js: no
// @testing-library/jest-dom (not installed — plain DOM assertions instead),
// and `fetch` is always stubbed so no test makes a real network request.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";

const gotoMock = vi.fn();
vi.mock("$app/navigation", () => ({
  goto: (...args) => gotoMock(...args),
}));

import RegisterPage from "./+page.svelte";

/**
 * Matches the fetch-response subset `apiFetch` (frontend/src/lib/api.js)
 * actually reads: `status`, `ok`, `text()`.
 * @param {{ status: number, body?: string }} opts
 */
function fakeResponse({ status, body = "" }) {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: () => Promise.resolve(body),
  };
}

async function fillFields({ email, password, passwordConfirm }) {
  if (email !== undefined) {
    await fireEvent.input(screen.getByLabelText(/^e-mail$/i), {
      target: { value: email },
    });
  }
  if (password !== undefined) {
    await fireEvent.input(screen.getByLabelText(/^mot de passe$/i), {
      target: { value: password },
    });
  }
  if (passwordConfirm !== undefined) {
    await fireEvent.input(screen.getByLabelText(/confirmer le mot de passe/i), {
      target: { value: passwordConfirm },
    });
  }
}

async function submit() {
  await fireEvent.click(screen.getByRole("button", { name: /créer un compte/i }));
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  gotoMock.mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("register page (#28)", () => {
  it("T-1: exposes one level-1 heading and labelled email/password/confirm fields", () => {
    render(RegisterPage);
    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0].textContent).toMatch(/inscription/i);

    expect(screen.getByLabelText(/^e-mail$/i).getAttribute("type")).toBe("email");
    expect(screen.getByLabelText(/^mot de passe$/i).getAttribute("type")).toBe("password");
    expect(screen.getByLabelText(/confirmer le mot de passe/i).getAttribute("type")).toBe(
      "password",
    );
  });

  it("T-2 (AC-1): submitting empty fields shows client-side errors and makes no network request", async () => {
    render(RegisterPage);
    await submit();

    const alert = screen.getByRole("alert");
    expect(alert.textContent).toMatch(/entrez votre adresse e-mail/i);
    expect(alert.textContent).toMatch(/entrez un mot de passe/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("T-3 (AC-1): a password shorter than 8 characters is rejected client-side", async () => {
    render(RegisterPage);
    await fillFields({ email: "new@example.com", password: "short1", passwordConfirm: "short1" });
    await submit();

    expect(screen.getByRole("alert").textContent).toMatch(/au moins 8 caractères/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("T-4 (AC-1): a mismatched confirmation is rejected client-side", async () => {
    render(RegisterPage);
    await fillFields({
      email: "new@example.com",
      password: "a-strong-password",
      passwordConfirm: "something-else",
    });
    await submit();

    expect(screen.getByRole("alert").textContent).toMatch(/mots de passe ne correspondent pas/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("T-5 (AC-2): submits email and password (not the confirmation) to the registration API and redirects on success", async () => {
    fetch.mockResolvedValue(fakeResponse({ status: 201, body: "{}" }));
    render(RegisterPage);

    await fillFields({
      email: "new@example.com",
      password: "a-strong-password",
      passwordConfirm: "a-strong-password",
    });
    await submit();

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/auth/register/");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({
      email: "new@example.com",
      password: "a-strong-password",
    });

    await vi.waitFor(() => expect(gotoMock).toHaveBeenCalledWith("/"));
  });

  it("T-6 (AC-2): a 400 response's field errors are surfaced to the user", async () => {
    fetch.mockResolvedValue(
      fakeResponse({
        status: 400,
        body: JSON.stringify({
          email: ["This field must be unique."],
        }),
      }),
    );
    render(RegisterPage);

    await fillFields({
      email: "taken@example.com",
      password: "a-strong-password",
      passwordConfirm: "a-strong-password",
    });
    await submit();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/email/i);
    expect(alert.textContent).toMatch(/must be unique/i);
    expect(gotoMock).not.toHaveBeenCalled();
  });

  it("T-7: a network failure (API unreachable) shows a generic, non-technical error", async () => {
    fetch.mockRejectedValue(new TypeError("Failed to fetch"));
    render(RegisterPage);

    await fillFields({
      email: "new@example.com",
      password: "a-strong-password",
      passwordConfirm: "a-strong-password",
    });
    await submit();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/impossible de joindre cashmire/i);
    expect(gotoMock).not.toHaveBeenCalled();
  });
});
