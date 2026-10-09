// Component tests for the login screen (#29).
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

import LoginPage from "./+page.svelte";

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

async function fillAndSubmit({ email, password }) {
  await fireEvent.input(screen.getByLabelText(/^e-mail$/i), {
    target: { value: email },
  });
  await fireEvent.input(screen.getByLabelText(/^mot de passe$/i), {
    target: { value: password },
  });
  await fireEvent.click(screen.getByRole("button", { name: /se connecter/i }));
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  gotoMock.mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("login page (#29)", () => {
  it("T-1: exposes exactly one level-1 heading and labelled email/password fields", () => {
    render(LoginPage);
    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0].textContent).toMatch(/connexion/i);

    const email = screen.getByLabelText(/^e-mail$/i);
    const password = screen.getByLabelText(/^mot de passe$/i);
    expect(email.tagName).toBe("INPUT");
    expect(email.getAttribute("type")).toBe("email");
    expect(password.getAttribute("type")).toBe("password");
  });

  it("T-2 (AC-2): empty fields show a client-side error and make no network request", async () => {
    render(LoginPage);
    await fireEvent.click(screen.getByRole("button", { name: /se connecter/i }));

    expect(screen.getByRole("alert").textContent).toMatch(
      /entrez votre e-mail et votre mot de passe/i,
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("T-3 (AC-1): submits credentials to the login API with the session cookie and redirects on success", async () => {
    fetch.mockResolvedValue(fakeResponse({ status: 200, body: "{}" }));
    render(LoginPage);

    await fillAndSubmit({ email: "jane@example.com", password: "correct-horse" });

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/auth/login/");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({
      email: "jane@example.com",
      password: "correct-horse",
    });

    await vi.waitFor(() => expect(gotoMock).toHaveBeenCalledWith("/"));
  });

  it("T-4 (AC-2): a 401 response shows a clear, non-technical error and does not redirect", async () => {
    fetch.mockResolvedValue(
      fakeResponse({ status: 401, body: JSON.stringify({ detail: "Invalid credentials" }) }),
    );
    render(LoginPage);

    await fillAndSubmit({ email: "jane@example.com", password: "wrong" });

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/e-mail ou mot de passe incorrect/i);
    // The server's own wording is never echoed (would hint whether the
    // account exists).
    expect(alert.textContent).not.toMatch(/invalid credentials/i);
    expect(gotoMock).not.toHaveBeenCalled();
  });

  it("T-5: a network failure (API unreachable) shows a generic, non-technical error", async () => {
    fetch.mockRejectedValue(new TypeError("Failed to fetch"));
    render(LoginPage);

    await fillAndSubmit({ email: "jane@example.com", password: "whatever1" });

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/impossible de joindre cashmire/i);
    expect(gotoMock).not.toHaveBeenCalled();
  });

  it("T-6: while submitting, the button is disabled and relabelled, and a second click does not double-submit", async () => {
    let resolveFetch;
    fetch.mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve;
      }),
    );
    render(LoginPage);

    await fireEvent.input(screen.getByLabelText(/^e-mail$/i), {
      target: { value: "jane@example.com" },
    });
    await fireEvent.input(screen.getByLabelText(/^mot de passe$/i), {
      target: { value: "correct-horse" },
    });
    await fireEvent.click(screen.getByRole("button", { name: /se connecter/i }));

    const button = screen.getByRole("button", { name: /connexion/i });
    expect(button.hasAttribute("disabled")).toBe(true);

    await fireEvent.click(button);
    expect(fetch).toHaveBeenCalledTimes(1);

    resolveFetch(fakeResponse({ status: 200, body: "{}" }));
    await vi.waitFor(() => expect(gotoMock).toHaveBeenCalled());
  });
});
