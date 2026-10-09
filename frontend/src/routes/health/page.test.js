// Component tests for the API health check screen.
// Covers docs/specs/issue-18-health-screen.md section 8.3, T-1 through T-11.
//
// No @testing-library/jest-dom matchers are used (toHaveAttribute,
// toHaveAccessibleName, etc.) — that package is not installed. See
// docs/reviews/issue-63-privacy-page.md and privacy/page.test.js for the
// precedent. Plain DOM assertions (`el.textContent`, `el.getAttribute(...)`)
// are used instead.
//
// Marker strings — defined once here per docs/specs/issue-18-health-screen.md
// section 8.3's closing note, so a wording change in +page.svelte (§5.2-§5.4)
// is a one-line edit here rather than a hunt through every test.
const LOADING_MARKER = "Interrogation"; // §5.2
const SUCCESS_MARKER = "est accessible"; // §5.3
const ERROR_MARKER = "Échec du contrôle"; // §5.4

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";

import HealthPage from "./+page.svelte";
import Layout from "../+layout.svelte";

// Svelte 5 documented pattern for supplying a `children` snippet prop from a
// test, reused from privacy/page.test.js rather than inventing a new one.
const emptyChildrenSnippet = createRawSnippet(() => ({
  render: () => `<div></div>`,
}));

beforeEach(() => {
  // No test may make a real network request (§8.2) — every test stubs
  // `fetch` before rendering.
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("health page (#18)", () => {
  it("T-1 (AC-1): exposes exactly one level-1 heading naming the page", () => {
    // Never-resolving fetch: we only care about the initial render here.
    fetch.mockReturnValue(new Promise(() => {}));
    render(HealthPage);
    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0].textContent).toMatch(/contrôle de l'état de l'api/i);
  });

  it("T-2 (AC-2): shows the loading state immediately, and only the loading state", () => {
    fetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(HealthPage);

    expect(screen.getByText(new RegExp(LOADING_MARKER))).toBeTruthy();
    expect(screen.queryByText(new RegExp(SUCCESS_MARKER))).toBeNull();
    expect(screen.queryByText(new RegExp(ERROR_MARKER))).toBeNull();
    // No Retry button in the loading state (§5.2 must-not list).
    expect(screen.queryByRole("button", { name: /retry/i })).toBeNull();
  });

  it("T-3 (AC-3): on a 2xx JSON response, shows success with the reported status and HTTP code", async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({ status: "ok" }),
    });
    render(HealthPage);

    await screen.findByText(new RegExp(SUCCESS_MARKER));
    expect(screen.getByText(/statut signalé : ok/i)).toBeTruthy();
    expect(screen.getByText(/http 200/i)).toBeTruthy();
    // T-8: the other two states' markers are absent.
    expect(screen.queryByText(new RegExp(LOADING_MARKER))).toBeNull();
    expect(screen.queryByText(new RegExp(ERROR_MARKER))).toBeNull();
  });

  it("T-4 (AC-4, §6.2): on a 404 response, shows the error state with the status code", async () => {
    fetch.mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Not found." }),
    });
    render(HealthPage);

    await screen.findByText(new RegExp(ERROR_MARKER));
    // "404" legitimately appears twice — in the error message and in the
    // dedicated "HTTP 404" line — so use the *All* variant.
    expect(screen.getAllByText(/404/).length).toBeGreaterThan(0);
    // T-8: success marker must not appear.
    expect(screen.queryByText(new RegExp(SUCCESS_MARKER))).toBeNull();
    expect(screen.queryByText(new RegExp(LOADING_MARKER))).toBeNull();
  });

  it("T-5 (AC-4, §6.1): when fetch rejects, shows the error state naming an unreachable API and the called URL", async () => {
    fetch.mockRejectedValue(new TypeError("Failed to fetch"));
    render(HealthPage);

    await screen.findByText(new RegExp(ERROR_MARKER));
    expect(screen.getByText(/impossible de joindre l'api/i)).toBeTruthy();
    // The called URL appears verbatim in the DOM (default base, no env
    // stub). It legitimately appears twice — once in the error message,
    // once in the dedicated "Called <url>" line — so use the *All* variant.
    expect(
      screen.getAllByText(/http:\/\/localhost:8000\/api\/health\//).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByText(new RegExp(SUCCESS_MARKER))).toBeNull();
    expect(screen.queryByText(new RegExp(LOADING_MARKER))).toBeNull();
  });

  it("T-6 (AC-4, §6.4): a non-JSON body produces the error state, not a success state with undefined", async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => {
        throw new SyntaxError("Unexpected token");
      },
    });
    render(HealthPage);

    await screen.findByText(new RegExp(ERROR_MARKER));
    expect(screen.queryByText(new RegExp(SUCCESS_MARKER))).toBeNull();
    expect(screen.queryByText("undefined")).toBeNull();
  });

  it("T-6b (AC-4, §6.4): a 200 body with no status key also produces the error state", async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({}),
    });
    render(HealthPage);

    await screen.findByText(new RegExp(ERROR_MARKER));
    expect(screen.getByText(/ne contenait pas de champ status/i)).toBeTruthy();
    expect(screen.queryByText(new RegExp(SUCCESS_MARKER))).toBeNull();
    expect(screen.queryByText("undefined")).toBeNull();
  });

  it("T-7 (AC-8, §6.3): a TimeoutError rejection shows the timeout message", async () => {
    const timeoutError = new DOMException("The operation timed out.", "TimeoutError");
    fetch.mockRejectedValue(timeoutError);
    render(HealthPage);

    await screen.findByText(new RegExp(ERROR_MARKER));
    expect(screen.getByText(/n'a pas répondu dans un délai de 8 secondes/i)).toBeTruthy();
    expect(screen.queryByText(new RegExp(SUCCESS_MARKER))).toBeNull();
    expect(screen.queryByText(new RegExp(LOADING_MARKER))).toBeNull();
  });

  it("T-9 (AC-6): builds the request URL from VITE_API_URL with fallback and trailing-slash normalisation", async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({ status: "ok" }),
    });
    render(HealthPage);
    await screen.findByText(new RegExp(SUCCESS_MARKER));

    expect(fetch.mock.calls[0][0]).toContain("/api/health/");
    expect(fetch.mock.calls[0][0]).not.toContain("//api");
  });

  it("T-9b (AC-6): a stubbed VITE_API_URL without a trailing slash is used as the base", async () => {
    vi.stubEnv("VITE_API_URL", "http://example.test:9999");
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({ status: "ok" }),
    });
    render(HealthPage);
    await screen.findByText(new RegExp(SUCCESS_MARKER));

    expect(fetch.mock.calls[0][0]).toBe("http://example.test:9999/api/health/");
  });

  it("T-9c (AC-6): a stubbed VITE_API_URL with a trailing slash is normalised to exactly one slash before api", async () => {
    vi.stubEnv("VITE_API_URL", "http://example.test:9999/");
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({ status: "ok" }),
    });
    render(HealthPage);
    await screen.findByText(new RegExp(SUCCESS_MARKER));

    const calledUrl = fetch.mock.calls[0][0];
    expect(calledUrl).toBe("http://example.test:9999/api/health/");
    expect(calledUrl.match(/\/api\//g)).toHaveLength(1);
  });

  it("T-10 (AC-7): Retry re-issues the request and can bring the page to success", async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ detail: "Not found." }),
    });
    render(HealthPage);

    await screen.findByText(new RegExp(ERROR_MARKER));
    const retryButton = screen.getByRole("button", { name: /réessayer/i });

    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({ status: "ok" }),
    });
    retryButton.click();

    await screen.findByText(new RegExp(SUCCESS_MARKER));
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("T-11 (AC-10): the shared layout footer links to /health and still links to /privacy", () => {
    // The layout itself now fetches GET /api/auth/me/ on mount (issue #104
    // follow-up, #26) for the auth-aware nav — this test doesn't exercise
    // that, so a bare 401 keeps it out of the way.
    fetch.mockResolvedValue({
      ok: false,
      status: 401,
      text: () =>
        Promise.resolve('{"detail":"Authentication credentials were not provided."}'),
    });
    render(Layout, { props: { children: emptyChildrenSnippet } });

    // Scoped to the contentinfo landmark: the header nav also has a
    // "Privacy" link to the same destination, so an unscoped query would
    // match both (see layout.test.js T-3 for the same precedent).
    const footer = screen.getByRole("contentinfo");

    const healthLink = within(footer).getByRole("link", { name: /état de l'api/i });
    expect(healthLink.getAttribute("href")).toBe("/health");

    const privacyLink = within(footer).getByRole("link", { name: /confidentialité/i });
    expect(privacyLink.getAttribute("href")).toBe("/privacy");
  });
});
