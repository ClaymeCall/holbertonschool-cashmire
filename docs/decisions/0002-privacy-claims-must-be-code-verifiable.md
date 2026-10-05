# 0002 — Public statements about data handling must be verifiable against the code

- **Status:** Proposed
- **Date:** 2026-10-05
- **Context issue:** #63 (privacy and legal information page)
- **Applies to:** every future feature that stores, transmits or processes data

## Context

Cashmire is about to publish a page that tells people how their data is handled.
Today the honest answer is "no personal data is collected or stored at all":
the backend defines no models, no migrations exist, the container never runs
`migrate`, the entire API is a health endpoint, and there is no registration or
login anywhere in the product.

Privacy pages rot in a specific and damaging way. They are written once,
describe the product the team *intends* to build, and are never revisited when
the product changes. The result is a published statement to users that is
false — sometimes false in the reassuring direction ("your data is encrypted")
and sometimes false in the understating direction ("we collect nothing") long
after a `User` table shipped.

Both directions are a problem, and neither is caught by ordinary code review,
because the privacy page lives in a different part of the tree from the feature
that invalidated it.

## Decision

1. **Every factual claim on a public data-handling page must be traceable to
   code in this repository.** The spec for issue #63 formalises this as a claims
   table: claim, evidence file, how to verify. Any claim without evidence is not
   published. This burden sits with the author of the page, not the reviewer.

2. **Security measures may only be claimed if implemented.** Encryption at rest,
   TLS, password hashing, access controls, audit logging, backups, data
   residency and compliance certifications are claimed only when a reviewer can
   point at the configuration or code that provides them. Aspiration is not
   implementation.

3. **Weaknesses that bear on user data are disclosed, not hidden.** The project
   currently defaults to `DEBUG=true`, `ALLOWED_HOSTS=*` and a hardcoded
   fallback `SECRET_KEY`, and mounts Django's admin. While that is true, the
   page says the project is not production-hardened. The remedy for an
   uncomfortable disclosure is to fix the code, not to soften the sentence.

4. **Unbuilt features are labelled as unbuilt.** Planned capabilities may be
   described, but only in explicitly future or negative framing, in a section
   marked as such. Present tense is reserved for what runs today.

5. **Updating the privacy page is part of the definition of done for any change
   that collects, stores, transmits or shares personal data.** Concretely, a PR
   that does any of the following must update the privacy page in the same PR,
   or state in its description why no update is needed:
   - adds or changes a model, field or migration that holds user-supplied data;
   - adds authentication, sessions, tokens or cookies;
   - adds a third-party service (analytics, email, error reporting, payments,
     bank aggregation, CDN, hosted fonts);
   - adds logging or telemetry that captures user data or identifiers;
   - changes data retention, deletion or export behaviour.

6. **The privacy page stays publicly reachable with no authentication, forever.**
   When auth is introduced, `/privacy` is not placed behind it, and must not be
   affected by any route guard.

7. **Values that only a human can supply are never invented by an agent.**
   Legal entity, contact address, jurisdiction, data-controller identity,
   hosting region and effective date are rendered as visible `[[PLACEHOLDER]]`
   tokens with a `TODO(#63-legal)` marker until a human fills them. A visibly
   unfinished page is strictly better than a plausibly wrong one.

8. **Legal sign-off is a human responsibility.** An agent may draft a privacy
   page; no agent-drafted privacy page is the operative policy until a human has
   read and approved it. The draft banner stays up until that happens.

## Consequences

- The privacy page becomes reviewable: a reviewer can diff claims against files
  instead of judging tone.
- Feature PRs that touch persistence carry a small extra obligation. That is the
  intended cost — it is the only point at which the page can be kept true.
- Enforcement is human review, not tooling. The one automated aid is a
  content-honesty test that fails if forbidden claims appear in the rendered
  page; it is a tripwire, not a guarantee, and it can be defeated by editing its
  allowlist. Reviewers should treat edits to that allowlist as significant.
- The page will read as more self-critical than a typical privacy policy for as
  long as the project runs on development defaults. Accepted.
