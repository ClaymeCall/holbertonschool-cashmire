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
// Rewritten for the French localization pass: the page is no longer a
// "draft pending legal review" with literal [[PLACEHOLDER]] tokens — it's a
// finished, French, fictive-but-plausible privacy page with invented
// values filled in (see +page.svelte's own comment). T-6 now asserts the
// opposite of before: no literal placeholder brackets remain.
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
    expect(headings[0].textContent).toMatch(/confidentialité/i);
  });

  it("T-2 (AC-2): every required section heading from docs/specs/issue-63-privacy-page.md section 5.1 is present, in order", () => {
    render(PrivacyPage);
    // Derived from the h2 headings actually implemented in +page.svelte.
    // If someone deletes a section, this fails.
    const requiredHeadings = [
      "En bref",
      "Les données que nous conservons",
      "Pourquoi nous les conservons",
      "Où vivent vos données",
      "Ce qu'il se passe quand vous visitez le site",
      "Cookies et suivi",
      "Les tiers avec qui nous partageons des données",
      "Combien de temps nous les conservons",
      "Vos droits",
      "Comment nous protégeons vos données",
      "Ce qui est prévu, et ce qui ne l'est pas encore",
      "Qui édite Cashmire",
      "Modifications de cette page",
    ];
    const renderedHeadings = screen
      .getAllByRole("heading", { level: 2 })
      .map((el) => el.textContent.trim());

    expect(renderedHeadings).toEqual(requiredHeadings);
  });

  it("T-3 (AC-4): contains no unsubstantiated security claim from docs/specs/issue-63-privacy-page.md section 5.3", () => {
    const { container } = render(PrivacyPage);
    const text = container.textContent.replace(/\s+/g, " ").toLowerCase();

    // This page never claims encryption-at-rest, TLS/HTTPS, bank
    // connections, or compliance certifications — it simply doesn't mention
    // them, rather than hedging about them at length (decision
    // 0002/R-7's underlying concern — no false claim — still holds, just
    // without the old draft's explicit "we do not claim X" sentences).
    const neverClaimed = [
      "chiffrées au repos", // encrypted at rest
      "tls",
      "https",
      "connexion bancaire",
      "transaction",
      "conforme au rgpd",
      "iso-27001",
    ];
    for (const phrase of neverClaimed) {
      expect(text.includes(phrase)).toBe(false);
    }
  });

  it("accurately discloses what the app actually stores and that records are deletable", () => {
    const { container } = render(PrivacyPage);
    const text = container.textContent.replace(/\s+/g, " ");

    expect(text).toContain("Cashmire vous permet de suivre vos dépenses et de fixer des budgets");
    expect(text).toContain(
      "un mot de passe chiffré (jamais stocké en clair",
    );
    expect(text).toContain(
      "Vous pouvez supprimer individuellement n'importe quelle dépense ou budget à tout moment",
    );
    expect(text).toContain("n'utilise ni outil d'analyse");
    // Never claims a feature that doesn't exist yet.
    expect(text).not.toContain("suppression de compte en un clic");
    expect(text).not.toContain("export automatique");
  });

  it("T-4 (AC-5): the shared layout footer links to /privacy with a self-describing name", () => {
    const { container } = render(Layout, { props: { children: emptyChildrenSnippet } });
    // Scoped to the footer specifically: issue #15 added a "Privacy" nav
    // link alongside this footer's "Privacy & legal" link, so an
    // unscoped `screen.getByRole` now matches both and throws. This test
    // is about the footer link (AC-5), not navigation, so scope to it.
    const footer = container.querySelector("footer");
    const link = within(footer).getByRole("link", { name: /confidentialité/i });
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

  it("T-6 (AC-8): every legal/contact value is a filled-in, non-placeholder string", () => {
    // Previously this page shipped with literal [[PLACEHOLDER]] tokens
    // pending a human legal decision; the French localization pass filled
    // them with plausible, invented values for this demo app (see
    // +page.svelte's LEGAL object) — assert none of the old bracket tokens
    // remain, and that the key values render somewhere on the page.
    render(PrivacyPage);
    const { container } = render(PrivacyPage);
    expect(container.textContent).not.toMatch(/\[\[[A-Z_]+\]\]/);
    expect(screen.getAllByText(/confidentialite@cashmire\.app/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Cashmire SAS/).length).toBeGreaterThan(0);
  });
});
