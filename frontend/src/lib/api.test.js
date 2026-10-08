// Covers docs/specs/issue-15-svelte-skeleton.md §6.1, T-5 through T-10b.
//
// Pure unit tests with a stubbed `globalThis.fetch` — no live server, no
// backend dependency.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import {
  API_BASE_URL,
  apiUrl,
  apiFetch,
  ApiError,
  resolveBaseUrl,
} from "./api.js";

/**
 * Build a minimal `Response`-shaped stub, matching the subset of the Fetch
 * API surface `apiFetch` actually reads (`status`, `ok`, `text()`).
 * @param {{ status: number, body?: string }} opts
 */
function fakeResponse({ status, body = "" }) {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: () => Promise.resolve(body),
  };
}

describe("resolveBaseUrl (T-5, T-6)", () => {
  it("T-5: falls back to the documented default when unset", () => {
    expect(resolveBaseUrl(undefined)).toBe("http://localhost:8000");
    expect(resolveBaseUrl(null)).toBe("http://localhost:8000");
    expect(resolveBaseUrl("")).toBe("http://localhost:8000");
    expect(resolveBaseUrl("   ")).toBe("http://localhost:8000");
  });

  it("T-6: uses a configured value and strips a trailing slash", () => {
    expect(resolveBaseUrl("https://api.example.com")).toBe(
      "https://api.example.com",
    );
    expect(resolveBaseUrl("https://api.example.com/")).toBe(
      "https://api.example.com",
    );
  });

  it("API_BASE_URL is the module-scope resolution of the real env", () => {
    // In this test run there is no frontend/.env, so VITE_API_URL is unset
    // and the public export must equal the documented default.
    expect(API_BASE_URL).toBe("http://localhost:8000");
  });
});

describe("apiUrl (T-7)", () => {
  it("T-7: joins with exactly one slash and preserves the caller's trailing slash", () => {
    expect(apiUrl("/api/health/")).toBe(`${API_BASE_URL}/api/health/`);
    expect(apiUrl("api/health/")).toBe(`${API_BASE_URL}/api/health/`);
    // No double slash either way.
    expect(apiUrl("/api/health/")).not.toMatch(/\/\/api/);
  });
});

describe("apiFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("T-8: resolves a 200 JSON body and calls fetch once with the expected absolute URL", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(fakeResponse({ status: 200, body: '{"status":"ok"}' }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiFetch("/api/health/");

    expect(result).toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/health/`);
    expect(init.method).toBe("GET");
    expect(init.headers.Accept).toBe("application/json");
  });

  it.each([400, 401, 403, 404, 500])(
    "T-9: a %i response rejects with ApiError carrying status and parsed body",
    async (status) => {
      const errorBody = { detail: `error ${status}` };
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(
          fakeResponse({ status, body: JSON.stringify(errorBody) }),
        ),
      );

      await expect(apiFetch("/api/health/")).rejects.toMatchObject({
        status,
        body: errorBody,
      });
      await expect(apiFetch("/api/health/")).rejects.toBeInstanceOf(ApiError);
    },
  );

  it("T-10: a fetch rejection (network down) surfaces as an ApiError with status 0", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(apiFetch("/api/health/")).rejects.toBeInstanceOf(ApiError);
    await expect(apiFetch("/api/health/")).rejects.toMatchObject({ status: 0 });
  });

  it("T-10: a 204 response resolves with null", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(fakeResponse({ status: 204 })));

    await expect(apiFetch("/api/health/")).resolves.toBeNull();
  });

  it("2xx with a non-JSON body rejects with ApiError carrying the raw text", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        fakeResponse({ status: 200, body: "<html>not json</html>" }),
      ),
    );

    await expect(apiFetch("/api/health/")).rejects.toMatchObject({
      status: 200,
      body: "<html>not json</html>",
    });
  });

  it("T-10b: a plain-object body is JSON-stringified with Content-Type application/json", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(fakeResponse({ status: 200, body: '{"ok":true}' }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/widgets/", { method: "POST", body: { name: "a" } });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ name: "a" }));
  });

  it("T-10b: FormData is passed through untouched with no Content-Type set", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(fakeResponse({ status: 200, body: '{"ok":true}' }));
    vi.stubGlobal("fetch", fetchMock);

    const formData = new FormData();
    formData.append("file", "contents");

    await apiFetch("/api/uploads/", { method: "POST", body: formData });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.body).toBe(formData);
    expect(init.headers["Content-Type"]).toBeUndefined();
  });

  it("merges caller headers, with the caller's values winning", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(fakeResponse({ status: 200, body: '{"ok":true}' }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/health/", { headers: { Accept: "text/plain" } });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.Accept).toBe("text/plain");
  });

  it("forwards signal/method/credentials unchanged", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(fakeResponse({ status: 200, body: '{"ok":true}' }));
    vi.stubGlobal("fetch", fetchMock);

    const controller = new AbortController();
    await apiFetch("/api/health/", {
      method: "DELETE",
      credentials: "same-origin",
      signal: controller.signal,
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("DELETE");
    expect(init.credentials).toBe("same-origin");
    expect(init.signal).toBe(controller.signal);
  });

  it("does not set credentials by default", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(fakeResponse({ status: 200, body: '{"ok":true}' }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/health/");

    const [, init] = fetchMock.mock.calls[0];
    expect(init.credentials).toBeUndefined();
  });

  it("never coerces a string money field to a number (money rule, §4.3.6)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        fakeResponse({ status: 200, body: '{"amount":"12.50"}' }),
      ),
    );

    const result = await apiFetch("/api/widgets/1/");
    expect(result.amount).toBe("12.50");
    expect(typeof result.amount).toBe("string");
  });

  // docs/decisions/0003-session-cookie-auth-strategy.md point 5: an unsafe
  // request on an authenticated session must carry the CSRF token back as
  // `X-CSRFToken`, read from the (non-HttpOnly) `csrftoken` cookie.
  describe("CSRF header (decision 0003, point 5)", () => {
    afterEach(() => {
      // jsdom's `document` is shared across this file's tests.
      document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    });

    it("attaches X-CSRFToken on an unsafe method when the cookie is present", async () => {
      document.cookie = "csrftoken=abc123";
      const fetchMock = vi.fn().mockResolvedValue(fakeResponse({ status: 204 }));
      vi.stubGlobal("fetch", fetchMock);

      await apiFetch("/api/expenses/1/", { method: "DELETE" });

      const [, init] = fetchMock.mock.calls[0];
      expect(init.headers["X-CSRFToken"]).toBe("abc123");
    });

    it("omits the header on a GET even when the cookie is present", async () => {
      document.cookie = "csrftoken=abc123";
      const fetchMock = vi
        .fn()
        .mockResolvedValue(fakeResponse({ status: 200, body: "{}" }));
      vi.stubGlobal("fetch", fetchMock);

      await apiFetch("/api/expenses/");

      const [, init] = fetchMock.mock.calls[0];
      expect(init.headers["X-CSRFToken"]).toBeUndefined();
    });

    it("omits the header on an unsafe method when there is no cookie yet", async () => {
      const fetchMock = vi
        .fn()
        .mockResolvedValue(fakeResponse({ status: 201, body: "{}" }));
      vi.stubGlobal("fetch", fetchMock);

      await apiFetch("/api/expenses/", { method: "POST", body: { amount: "1.00" } });

      const [, init] = fetchMock.mock.calls[0];
      expect(init.headers["X-CSRFToken"]).toBeUndefined();
    });

    it("lets a caller-supplied header win over the cookie-derived one", async () => {
      document.cookie = "csrftoken=abc123";
      const fetchMock = vi.fn().mockResolvedValue(fakeResponse({ status: 204 }));
      vi.stubGlobal("fetch", fetchMock);

      await apiFetch("/api/expenses/1/", {
        method: "DELETE",
        headers: { "X-CSRFToken": "caller-value" },
      });

      const [, init] = fetchMock.mock.calls[0];
      expect(init.headers["X-CSRFToken"]).toBe("caller-value");
    });
  });
});
