// T-1 and T-4 do not rely on @testing-library/jest-dom matchers
// (toHaveAccessibleName, toHaveAttribute), which were used but never
// installed or imported — see docs/specs/issue-63-privacy-page.md section
// 8.2, which prefers doing without that dependency. T-3 normalizes
// textContent whitespace before matching the allowlist, because
// +page.svelte wraps long sentences across source lines, which otherwise
// left raw newlines/indentation in textContent and made every single-spaced
// allowlist phrase fail to match (a false positive that would have flagged
// the page as making forbidden claims it does not make).
//
// Covers docs/specs/issue-63-privacy-page.md section 8.3, T-1 through T-6.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";

import PrivacyPage from "./+page.svelte";
import Layout from "../+layout.svelte";

// Svelte 5 documented pattern for supplying a `children` snippet prop from a
// test: https://svelte.dev/docs/svelte/testing
const emptyChildrenSnippet = createRawSnippet(() => ({
  render: () => `<div></div>`,
}));

describe("privacy page (#63)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("T-1 (AC-1): exposes exactly one level-1 heading naming the page", () => {
    render(PrivacyPage);
    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    // Plain DOM assertion in place of the jest-dom `toHaveAccessibleName`
    // matcher, which is not installed (see header comment).
    expect(headings[0].textContent).toMatch(/privacy/i);
  });

  it("T-2 (AC-2): every required section heading from docs/specs/issue-63-privacy-page.md section 5.1 is present, in order", () => {
    render(PrivacyPage);
    // Derived from the h2 headings actually implemented in +page.svelte.
    // If someone deletes a section, this fails.
    const requiredHeadings = [
      "The short version",
      "What personal data we store",
      "Why we store it",
      "Where data would live",
      "What happens when you visit this site",
      "Cookies and tracking",
      "Third parties we share data with",
      "How long we keep data",
      "Your rights",
      "How we protect data",
      "What is planned, and not yet built",
      "Who operates Cashmire",
      "Changes to this page",
    ];
    const renderedHeadings = screen
      .getAllByRole("heading", { level: 2 })
      .map((el) => el.textContent.trim());

    expect(renderedHeadings).toEqual(requiredHeadings);
  });

  it("T-3 (AC-4): contains no forbidden claim from docs/specs/issue-63-privacy-page.md section 5.3, outside the allowlisted negated sentences", () => {
    const { container } = render(PrivacyPage);
    // Collapse all whitespace (including the newlines/indentation that
    // textContent preserves from sentences wrapped across source lines in
    // +page.svelte) to single spaces before matching, so the single-spaced
    // allowlist phrases below can actually match.
    const text = container.textContent.replace(/\s+/g, " ").toLowerCase();

    // docs/specs/issue-63-privacy-page.md section 5.3 forbidden tokens. Each entry's `allow` list is the
    // exact negated/forward-looking phrase(s) this page uses. Removing a
    // phrase here without removing the matching sentence in +page.svelte (or
    // vice versa) is a deliberate, reviewable edit — see
    // docs/decisions/0002-privacy-claims-must-be-code-verifiable.md and R-7.
    const forbidden = [
      {
        token: "encrypt",
        allow: ["it does not say that data is encrypted at rest"],
      },
      {
        token: "tls",
        allow: ["it does not say that traffic is served over tls or https"],
      },
      {
        token: "https",
        allow: ["it does not say that traffic is served over tls or https"],
      },
      // "hash" and "password" are no longer forbidden tokens: accounts and
      // passwords are real now (#22/#23 registration/login), and password
      // hashing via Django's AbstractUser is an implemented, verifiable
      // security measure (decision 0002 point 2 permits claiming it once
      // implemented) rather than an aspirational claim about a feature that
      // didn't exist. See the "How we protect data" section.
      { token: "bank", allow: ["no bank connection", "no bank aggregator"] },
    ];

    for (const { token, allow } of forbidden) {
      if (!text.includes(token)) continue;
      let remaining = text;
      // Strip longest phrases first. Some entries' allow phrases overlap as
      // substrings (e.g. "no password" is a substring of the longer "it does
      // not say that passwords are hashed (there are no passwords to hash)"
      // sentence via its "...there are no passwords to hash)" tail). Removing
      // the short phrase first would eat the "no password" inside the long
      // sentence and leave an orphaned "passwords are hashed" behind, which
      // still contains the token and would produce a false positive. Sorting
      // by descending length guarantees a longer phrase is always removed as
      // one unit before any shorter phrase can partially consume it. Do not
      // simplify this back to iterating `allow` in declared order.
      for (const phrase of [...allow].sort((a, b) => b.length - a.length)) {
        remaining = remaining.split(phrase.toLowerCase()).join("");
      }
      expect(remaining.includes(token)).toBe(false);
    }

    // Tokens that must never appear at all, in any form, on this page.
    const alwaysForbidden = ["transaction", "gdpr-compliant", "iso-27001"];
    for (const token of alwaysForbidden) {
      expect(text.includes(token)).toBe(false);
    }
  });

  it("accurately discloses expense creation and its storage conditions", () => {
    const { container } = render(PrivacyPage);
    const text = container.textContent.replace(/\s+/g, " ");

    expect(text).toContain(
      "The API accepts expense records at POST /api/expenses/",
    );
    expect(text).toContain(
      "It can store an amount, date, optional description, category, and the owning user in PostgreSQL",
    );
    expect(text).toContain(
      "The endpoint requires an authenticated Django session",
    );
    expect(text).toContain(
      "The authenticated API lets the owner create, list, edit, and delete expense records",
    );
    expect(text).toContain(
      "No retention period or automatic deletion schedule for expense records is defined",
    );
    expect(text).toContain(
      "An authenticated owner can delete an individual expense through the API",
    );
    expect(text).not.toContain("Nothing is kept");
    expect(text).not.toContain("listing, editing, and deleting expenses are not implemented yet");
    expect(text).not.toContain("The API has no expense deletion endpoint");
  });

  it("T-4 (AC-5): the shared layout footer links to /privacy with a self-describing name", () => {
    const { container } = render(Layout, { props: { children: emptyChildrenSnippet } });
    // Scoped to the footer specifically: issue #15 added a "Privacy" nav
    // link alongside this footer's "Privacy & legal" link, so an
    // unscoped `screen.getByRole` now matches both and throws. This test
    // is about the footer link (AC-5), not navigation, so scope to it.
    const footer = container.querySelector("footer");
    const link = within(footer).getByRole("link", { name: /privacy/i });
    // Plain DOM assertion in place of the jest-dom `toHaveAttribute` matcher,
    // which is not installed (see header comment).
    expect(link.getAttribute("href")).toBe("/privacy");
  });

  it("T-5 (AC-7): rendering the privacy page issues zero network requests", () => {
    // jsdom environments on Node 18+ provide a global `fetch`, but spying on
    // it requires the property to already exist — guard against an
    // environment where it does not, rather than letting `vi.spyOn` throw.
    if (typeof globalThis.fetch !== "function") {
      globalThis.fetch = () =>
        Promise.reject(new Error("fetch should not be called in this test"));
    }
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(PrivacyPage);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("T-6 (AC-8): human-dependent values render as literal [[PLACEHOLDER]] tokens", () => {
    // Expected to be updated (and trimmed) once a human supplies real values
    // per docs/specs/issue-63-privacy-page.md section 10.1 — that future edit is not someone defeating
    // this test.
    render(PrivacyPage);
    expect(screen.getAllByText(/\[\[CONTACT_EMAIL\]\]/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/\[\[LEGAL_ENTITY\]\]/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/\[\[JURISDICTION\]\]/).length).toBeGreaterThan(0);
  });
});
