// Covers docs/specs/issue-15-svelte-skeleton.md §6.2, T-1 through T-4b.
//
// Follows the existing colocation/testing convention set by
// frontend/src/routes/privacy/page.test.js: @testing-library/svelte +
// createRawSnippet for the `children` prop, no @testing-library/jest-dom
// (not installed — plain DOM assertions instead).
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { writable } from "svelte/store";
import { setCurrentUser } from "$lib/auth.svelte.js";

// `$app/stores`' `page` is mocked with a real Svelte store so the current
// pathname can be controlled per test (T-4) via `.set()`, and so the
// component's `$page` auto-subscription works exactly as it would against
// the real store. See +layout.svelte's script comment for why this project
// uses `$app/stores` rather than `$app/state` here.
//
// `writable` is a named import (not a locally declared variable), so it is
// safe to reference inside the `vi.mock` factory despite the factory being
// hoisted above this file's other statements.
vi.mock("$app/stores", () => ({
  page: writable({ url: new URL("http://localhost/") }),
}));

const gotoMock = vi.fn();
vi.mock("$app/navigation", () => ({
  goto: (...args) => gotoMock(...args),
}));

import { page as pageStore } from "$app/stores";
import Layout from "./+layout.svelte";

const childrenSnippet = (html) =>
  createRawSnippet(() => ({
    render: () => html,
  }));

/**
 * Stubs `globalThis.fetch` so the layout's mount-time `GET /api/auth/me/`
 * (issue #104 follow-up, #26) resolves deterministically instead of
 * attempting a real network call. Defaults to 401 (anonymous) — the common
 * case most tests below assume unless they call this again themselves.
 * Returns the mock so callers can assert on `.mock.calls`.
 * @param {{ status?: number, body?: unknown }} [opts]
 */
function stubCurrentUserFetch({
  status = 401,
  body = { detail: "Authentication credentials were not provided." },
} = {}) {
  const fetchMock = vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    text: () => Promise.resolve(status === 204 ? "" : JSON.stringify(body)),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("app shell layout (#15, auth-aware nav follow-up)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    gotoMock.mockClear();
    pageStore.set({ url: new URL("http://localhost/") });
    // Reset the shared auth-state module between tests — it's a
    // module-level singleton, not component-local state.
    setCurrentUser(null);
    stubCurrentUserFetch();
  });

  it("T-1 (AC-4): while anonymous, the nav contains links to /, /privacy, /login and /register", () => {
    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    const nav = screen.getByRole("navigation", { name: /main/i });
    const hrefs = within(nav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));

    expect(hrefs).toContain("/");
    expect(hrefs).toContain("/privacy");
    // Added for #28/#29.
    expect(hrefs).toContain("/login");
    expect(hrefs).toContain("/register");
  });

  it("Expenses and Budgets links are always present, logged in or not", () => {
    const { unmount } = render(Layout, {
      props: { children: childrenSnippet("<div></div>") },
    });

    let nav = screen.getByRole("navigation", { name: /main/i });
    let hrefs = within(nav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));
    expect(hrefs).toContain("/expenses");
    expect(hrefs).toContain("/budgets");
    unmount();

    setCurrentUser({ id: 1, email: "demo@example.com" });
    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    nav = screen.getByRole("navigation", { name: /main/i });
    hrefs = within(nav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));
    expect(hrefs).toContain("/expenses");
    expect(hrefs).toContain("/budgets");
  });

  it("clicking Expenses or Budgets while anonymous redirects to /login instead of navigating there", () => {
    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    const nav = screen.getByRole("navigation", { name: /main/i });
    within(nav).getByRole("link", { name: "Expenses" }).click();
    expect(gotoMock).toHaveBeenCalledWith("/login");

    gotoMock.mockClear();
    within(nav).getByRole("link", { name: "Budgets" }).click();
    expect(gotoMock).toHaveBeenCalledWith("/login");
  });

  it("clicking Expenses or Budgets while logged in navigates normally, not to /login", () => {
    setCurrentUser({ id: 1, email: "demo@example.com" });
    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    const nav = screen.getByRole("navigation", { name: /main/i });
    within(nav).getByRole("link", { name: "Expenses" }).click();
    within(nav).getByRole("link", { name: "Budgets" }).click();

    expect(gotoMock).not.toHaveBeenCalledWith("/login");
  });

  it("T-2 (AC-4): the children snippet renders between the header and the footer, in document order", () => {
    const { container } = render(Layout, {
      props: {
        children: childrenSnippet('<p data-testid="page-content">hi</p>'),
      },
    });

    const header = container.querySelector("header");
    const footer = container.querySelector("footer");
    const content = screen.getByTestId("page-content");

    expect(header).not.toBeNull();
    expect(footer).not.toBeNull();

    // header precedes content precedes footer, in that exact document order.
    // eslint-disable-next-line no-bitwise
    expect(
      header.compareDocumentPosition(content) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    // eslint-disable-next-line no-bitwise
    expect(
      footer.compareDocumentPosition(content) & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
  });

  it("T-3 (AC-6): the footer still links to /privacy with a self-describing accessible name", () => {
    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    // Scoped to the contentinfo landmark: the header nav now also has a
    // "Privacy" link to the same destination, so an unscoped query would
    // match both.
    const footer = screen.getByRole("contentinfo");
    const link = within(footer).getByRole("link", { name: /privacy/i });
    expect(link.getAttribute("href")).toBe("/privacy");
  });

  it("T-4 (AC-5): exactly one nav link is aria-current, matching the mocked path", () => {
    pageStore.set({ url: new URL("http://localhost/") });
    const { unmount } = render(Layout, {
      props: { children: childrenSnippet("<div></div>") },
    });

    const nav = screen.getByRole("navigation", { name: /main/i });
    let current = within(nav)
      .getAllByRole("link")
      .filter((link) => link.getAttribute("aria-current") === "page");
    expect(current).toHaveLength(1);
    expect(current[0].getAttribute("href")).toBe("/");
    unmount();

    pageStore.set({ url: new URL("http://localhost/privacy") });
    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    const navAfter = screen.getByRole("navigation", { name: /main/i });
    current = within(navAfter)
      .getAllByRole("link")
      .filter((link) => link.getAttribute("aria-current") === "page");
    expect(current).toHaveLength(1);
    expect(current[0].getAttribute("href")).toBe("/privacy");
  });

  it("T-4b: mounting the layout fetches the current user exactly once, from /api/auth/me/", () => {
    // Supersedes the original #15 assertion ("zero fetch calls") — the nav
    // can't be auth-aware without resolving who's logged in, and the
    // layout is the one place that's resolved once per full page load
    // rather than every page re-deriving it.
    const fetchMock = stubCurrentUserFetch();

    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/auth/me/");
  });

  it("while logged in, Log in/Register are replaced by a Log out action", async () => {
    setCurrentUser({ id: 1, email: "demo@example.com" });

    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    const nav = screen.getByRole("navigation", { name: /main/i });
    const hrefs = within(nav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));
    expect(hrefs).not.toContain("/login");
    expect(hrefs).not.toContain("/register");
    expect(hrefs).toContain("/");
    expect(hrefs).toContain("/privacy");

    expect(
      within(nav).getByRole("button", { name: /log out/i }),
    ).not.toBeNull();
  });

  it("clicking Log out calls POST /api/auth/logout/ and restores Log in/Register", async () => {
    setCurrentUser({ id: 1, email: "demo@example.com" });
    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    const nav = screen.getByRole("navigation", { name: /main/i });
    const logoutButton = within(nav).getByRole("button", { name: /log out/i });

    const fetchMock = stubCurrentUserFetch({ status: 204 });
    logoutButton.click();

    await vi.waitFor(() => {
      expect(
        within(screen.getByRole("navigation", { name: /main/i })).queryByRole(
          "button",
          { name: /log out/i },
        ),
      ).toBeNull();
    });

    const hrefsAfter = within(screen.getByRole("navigation", { name: /main/i }))
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));
    expect(hrefsAfter).toContain("/login");
    expect(hrefsAfter).toContain("/register");

    const logoutCall = fetchMock.mock.calls.find(
      ([callUrl]) => callUrl === "http://localhost:8000/api/auth/logout/",
    );
    expect(/** @type {RequestInit} */ (logoutCall?.[1])?.method).toBe("POST");
    expect(gotoMock).toHaveBeenCalledWith("/");
  });
});
