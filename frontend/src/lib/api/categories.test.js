import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { API_BASE_URL } from "$lib/api";
import { listCategories } from "./categories.js";

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

describe("listCategories", () => {
  it("GETs /api/categories/ with the session credential and returns the array", async () => {
    const categories = [{ id: 1, name: "Alimentation" }];
    fetch.mockResolvedValue(
      fakeResponse({ status: 200, body: JSON.stringify({ categories }) }),
    );

    await expect(listCategories()).resolves.toEqual(categories);

    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe(`${API_BASE_URL}/api/categories/`);
    expect(init.credentials).toBe("include");
  });
});
