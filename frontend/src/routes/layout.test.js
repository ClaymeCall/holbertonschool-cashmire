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

import { page as pageStore } from "$app/stores";
import Layout from "./+layout.svelte";

const childrenSnippet = (html) =>
  createRawSnippet(() => ({
    render: () => html,
  }));

describe("app shell layout (#15)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    pageStore.set({ url: new URL("http://localhost/") });
  });

  it("T-1 (AC-4): a navigation landmark contains links to / and /privacy", () => {
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

  it("T-4b: rendering the layout issues zero fetch calls", () => {
    if (typeof globalThis.fetch !== "function") {
      globalThis.fetch = () =>
        Promise.reject(new Error("fetch should not be called in this test"));
    }
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(Layout, { props: { children: childrenSnippet("<div></div>") } });

    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
