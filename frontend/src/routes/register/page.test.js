// Component tests for the registration screen (#28).
//
// Same conventions as frontend/src/routes/health/page.test.js: no
// @testing-library/jest-dom (not installed — plain DOM assertions instead),
// and `fetch` is always stubbed so no test makes a real network request.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";

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
    await fireEvent.input(screen.getByLabelText(/^email$/i), {
      target: { value: email },
    });
  }
  if (password !== undefined) {
    await fireEvent.input(screen.getByLabelText(/^password$/i), {
      target: { value: password },
    });
  }
  if (passwordConfirm !== undefined) {
    await fireEvent.input(screen.getByLabelText(/confirm password/i), {
      target: { value: passwordConfirm },
    });
  }
}

async function submit() {
  await fireEvent.click(screen.getByRole("button", { name: /create account/i }));
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
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
    expect(headings[0].textContent).toMatch(/register/i);

    expect(screen.getByLabelText(/^email$/i).getAttribute("type")).toBe("email");
    expect(screen.getByLabelText(/^password$/i).getAttribute("type")).toBe("password");
    expect(screen.getByLabelText(/confirm password/i).getAttribute("type")).toBe(
      "password",
    );
  });

  it("T-2 (AC-1): submitting empty fields shows client-side errors and makes no network request", async () => {
    render(RegisterPage);
    await submit();

    const alert = screen.getByRole("alert");
    expect(alert.textContent).toMatch(/enter your email address/i);
    expect(alert.textContent).toMatch(/enter a password/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("T-3 (AC-1): a password shorter than 8 characters is rejected client-side", async () => {
    render(RegisterPage);
    await fillFields({ email: "new@example.com", password: "short1", passwordConfirm: "short1" });
    await submit();

    expect(screen.getByRole("alert").textContent).toMatch(/at least 8 characters/i);
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

    expect(screen.getByRole("alert").textContent).toMatch(/passwords do not match/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("T-5 (AC-2): submits email and password and shows the same neutral follow-up on 202", async () => {
    fetch.mockResolvedValue(
      fakeResponse({
        status: 202,
        body: JSON.stringify({
          detail: "If registration can be completed, sign in to continue.",
        }),
      }),
    );
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

    expect((await screen.findByRole("status")).textContent).toMatch(
      /if registration can be completed, you can now sign in/i,
    );
    expect(screen.getByRole("link", { name: /go to sign in/i }).getAttribute("href")).toBe(
      "/login",
    );
  });

  it("T-6 (AC-2): non-enumerating validation errors are surfaced to the user", async () => {
    fetch.mockResolvedValue(
      fakeResponse({
        status: 400,
        body: JSON.stringify({
          password: ["This password is too short."],
        }),
      }),
    );
    render(RegisterPage);

    await fillFields({
      email: "new@example.com",
      password: "a-strong-password",
      passwordConfirm: "a-strong-password",
    });
    await submit();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/password/i);
    expect(alert.textContent).toMatch(/too short/i);
  });

  it("shows an actionable retry message when registration is throttled", async () => {
    fetch.mockResolvedValue(fakeResponse({ status: 429, body: "{}" }));
    render(RegisterPage);

    await fillFields({
      email: "new@example.com",
      password: "a-strong-password",
      passwordConfirm: "a-strong-password",
    });
    await submit();

    expect((await screen.findByRole("alert")).textContent).toMatch(/wait a minute/i);
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
    expect(alert.textContent).toMatch(/couldn't reach cashmire/i);
  });
});
