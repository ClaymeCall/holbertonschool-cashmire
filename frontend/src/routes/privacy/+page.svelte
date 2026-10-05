<script>
  // TODO(#63-legal): these values require a human decision - see SPEC.md section 10.
  // Do not invent values. Do not remove this comment while any value is unresolved.
  const LEGAL = {
    entity: "[[LEGAL_ENTITY]]",
    status: "[[PROJECT_STATUS]]",
    contact: "[[CONTACT_EMAIL]]",
    jurisdiction: "[[JURISDICTION]]",
    controller: "[[DATA_CONTROLLER]]",
    hosting: "[[HOSTING_ARRANGEMENT]]",
    updated: "[[EFFECTIVE_DATE]]",
  };
</script>

<svelte:head>
  <title>Privacy and legal information · Cashmire</title>
  <meta
    name="description"
    content="What personal data Cashmire collects, why, where it would live, and how it is protected."
  />
</svelte:head>

<main>
  <h1>Privacy and legal information</h1>

  <p class="draft-banner">
    <strong>Draft — pending legal review.</strong> This page has not been approved
    by a human and is not yet the operative policy. Several values below are shown
    as literal placeholder tokens like <code>[[CONTACT_EMAIL]]</code> because they
    require a human decision; this notice stays up until every placeholder is
    filled in.
  </p>

  <p>Last updated: <time>{LEGAL.updated}</time></p>

  <h2>The short version</h2>
  <p>
    Cashmire does not currently ask you for any personal information, and it
    stores none. It is an early-stage project — the features that would
    eventually handle financial data are not built yet. The sections below
    explain this in detail.
  </p>

  <h2>What personal data we store</h2>
  <p>Today: none.</p>
  <ul>
    <li>No account</li>
    <li>No name</li>
    <li>No email address</li>
    <li>No password</li>
    <li>No expense record</li>
    <li>No budget</li>
    <li>No bank connection</li>
  </ul>
  <p>
    There is no form on this site to enter any of that. The one other page on
    this site simply shows whether the project's own API is responding.
  </p>

  <h2>Why we store it</h2>
  <p>
    Nothing is collected today, so there is nothing to justify. Going forward,
    the principle is this: data will be collected only where a named feature
    needs it, and this page will be updated before such a feature ships.
  </p>

  <h2>Where data would live</h2>
  <p>
    A PostgreSQL database is configured for this project. The application
    defines no tables in it. The backend container starts the web server
    without running database migrations, so as shipped, not even the
    framework's own tables are created. <em>Configured</em> is not the same
    thing as <em>populated</em>: the database holds nothing about you today.
  </p>

  <h2>What happens when you visit this site</h2>
  <p>
    The home page makes exactly one request, to this project's own
    <code>/api/health/</code> endpoint, which replies with
    <code>{'{"status": "ok"}'}</code> and nothing about you.
    <strong>This privacy page makes no requests at all.</strong>
  </p>
  <p>
    Like any web server, the server sees the usual connection metadata (IP
    address, user agent), and the development server prints request lines to
    its own console. No logging configuration, log storage, or log retention
    policy is defined in this project — so this page does not claim "we log
    nothing", and it does not claim any particular retention period for logs,
    because neither would be true.
  </p>

  <h2>Cookies and tracking</h2>
  <p>
    The application code sets no cookies and includes no analytics, no tag
    manager, no tracking pixel, no third-party script, and no third-party font
    or other asset.
  </p>
  <p>
    One caveat, because it is true: Django's standard admin interface is
    mounted at <code>/admin/</code> and would set a session cookie for anyone
    who logged into it — but there are no user accounts, that interface is not
    part of the product, and it is unrelated to using this site.
  </p>

  <h2>Third parties we share data with</h2>
  <p>
    None. There is no analytics provider, no email provider, no payment
    processor, no bank aggregator, no error-reporting service, and no CDN.
    Nothing is shared because nothing is collected.
  </p>
  <p>Hosting arrangement: <code>{LEGAL.hosting}</code>.</p>

  <h2>How long we keep data</h2>
  <p>
    Nothing is kept, so there is nothing to retain or expire. There is no
    account to delete, because there are no accounts. When features that
    store data ship, this section will state real retention periods — a
    decision for a human, not a default.
  </p>

  <h2>Your rights</h2>
  <p>
    Readers of a privacy page are typically entitled to rights such as access,
    rectification, erasure, restriction, portability, objection, and the
    ability to complain to a supervisory authority. In practice, there is
    currently no data of yours held to access, correct, export, or erase.
  </p>
  <p>
    To ask a question or exercise any of these rights, the contact route is:
    <code>{LEGAL.contact}</code>. Which legal regime applies is not yet
    settled: <code>{LEGAL.jurisdiction}</code>.
  </p>

  <h2>How we protect data</h2>
  <p>
    The strongest protection currently in place is that there is nothing to
    protect: no personal data is collected, so none can be lost, leaked, or
    misused.
  </p>
  <p>
    Browser access to the project's API is limited by a CORS allowlist that,
    by default, permits only the local development frontend. That is a
    development-time configuration, not a security guarantee — CORS is a
    browser policy, not a server-side access control.
  </p>
  <p>
    Cashmire currently runs with development defaults that are not safe for
    production: debug mode is on by default, the allowed-hosts setting
    accepts any host, and the secret key falls back to a hardcoded
    development value when none is configured. This page makes no claim to a
    hardened production security posture, and the project should not be
    treated as production-ready. Hardening must happen before any real user
    data is accepted.
  </p>
  <p>
    To be explicit about what this page does not claim: it does not say that
    data is encrypted at rest; it does not say that traffic is served over
    TLS or HTTPS; it does not say that passwords are hashed (there are no
    passwords to hash); and it does not say that access to data is
    role-restricted or audited. None of that is built, so none of it is
    claimed.
  </p>

  <h2>What is planned, and not yet built</h2>
  <p>
    User accounts, expense tracking, budgets, and categories are planned and
    do not exist in the software today. When they ship, they will involve
    storing personal and financial data, and this page will be updated at
    that time.
  </p>

  <h2>Who operates Cashmire</h2>
  <ul>
    <li>Operator: <code>{LEGAL.entity}</code></li>
    <li>Status: <code>{LEGAL.status}</code></li>
    <li>Data controller: <code>{LEGAL.controller}</code></li>
    <li>Governing jurisdiction / supervisory authority: <code>{LEGAL.jurisdiction}</code></li>
    <li>Contact: <code>{LEGAL.contact}</code></li>
  </ul>

  <h2>Changes to this page</h2>
  <p>
    Changes to this page are tracked in the project's git history. The
    last-updated date at the top reflects the most recent change. No email
    notification mechanism exists or is promised.
  </p>

  <p><a href="/">Back to the Cashmire home page</a></p>
</main>

<style>
  main {
    max-width: 70ch;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
    line-height: 1.5;
  }

  .draft-banner {
    border: 2px solid #7a4b00;
    background: #fff6e5;
    color: #3b2200;
    padding: 0.75rem 1rem;
    border-radius: 4px;
  }

  a {
    color: #0b3d91;
  }

  a:focus-visible {
    outline: 3px solid #0b3d91;
    outline-offset: 2px;
  }

  code {
    font-size: 0.95em;
  }
</style>
