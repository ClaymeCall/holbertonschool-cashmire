<script>
  import "$lib/styles/tokens.css";

  // TODO(#63-legal): these values require a human decision - see docs/specs/issue-63-privacy-page.md section 10.
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
    content="What personal data Cashmire collects, why, where it lives, and how it is protected."
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
    The API accepts expense records at <code>POST /api/expenses/</code>
    from an authenticated session. It can store an amount, date, optional
    description, category, and the owning user in PostgreSQL when the
    required migration has been applied. The same is true of budget records
    at <code>POST /api/budgets/</code>. Registration and login are
    implemented — the website has a working account registration page, a
    login page, and forms for adding expenses and setting budgets.
  </p>

  <h2>What personal data we store</h2>
  <p>
    Cashmire can process and store the data you give it when you create an
    account and use the expense and budget features. The code does not
    reveal whether a particular deployment's database currently contains
    any records — that depends on who has signed up and what they have
    entered.
  </p>
  <ul>
    <li>
      Account email address, and a password (hashed, not stored as plain
      text — see "How we protect data" below)
    </li>
    <li>Expense amount, date, and optional description</li>
    <li>Budget amount, period (start and end dates), and optional alert threshold</li>
    <li>Category and the user account associated with each expense or budget</li>
  </ul>
  <p>
    Registration (<code>POST /api/auth/register/</code>), login
    (<code>POST /api/auth/login/</code>), and logout
    (<code>POST /api/auth/logout/</code>) are implemented, with working
    pages for all three on the website. The endpoint requires an
    authenticated Django session, and so do the budget endpoints — which
    registering or logging in now provides. The application container does
    not apply database migrations on startup; the database must have the
    required migrations applied for submissions to be stored successfully.
  </p>

  <h2>Why we store it</h2>
  <p>
    An account's email and password exist so you can register once, then
    log back in to see your own data and nobody else's. Expense records
    support the expense-tracking feature: recording an amount, date, and
    optional description under a category for the authenticated user. The
    authenticated API lets the owner create, list, edit, and delete expense
    records, and the website provides a form for each of those operations.
    The same is true of budget records: an amount, period, and optional
    alert threshold under a category, with create/list/edit/delete forms on
    the website as well.
  </p>

  <h2>Where data would live</h2>
  <p>
    PostgreSQL is configured for this project. The application defines
    models and migrations for users, categories, expenses, and budgets. The
    expense and budget endpoints write to their respective tables once
    those migrations are applied. The backend container starts the web
    server without automatically applying migrations, so the schema in a
    particular database depends on which migrations its operator has
    applied.
  </p>

  <h2>What happens when you visit this site</h2>
  <p>
    For a logged-out visitor, the home page makes exactly one request, to
    this project's own <code>/api/health/</code> endpoint, which replies
    with <code>{'{"status": "ok"}'}</code> and nothing about you. If you are
    logged in, the home page additionally requests your own recent expenses
    and budgets — the same authenticated endpoints described above — to show
    them to you; that data is never sent anywhere else.
    <strong>This privacy page itself makes no requests at all.</strong>
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
    The application includes no analytics, tag manager, tracking pixel,
    third-party script, or third-party font or other asset. Logging in or
    registering sets two first-party cookies: a <code>sessionid</code>
    cookie that identifies your session (marked <code>HttpOnly</code>, so
    page JavaScript cannot read it) and a <code>csrftoken</code> cookie used
    only to protect state-changing requests (expense/budget create, edit,
    delete, and logout) from cross-site request forgery. Neither cookie is
    used for tracking, analytics, or advertising, and nothing is sent to a
    third party.
  </p>
  <p>
    One caveat, because it is true: Django's standard admin interface is
    mounted at <code>/admin/</code> and uses Django sessions for authenticated
    administrators. The admin interface is not part of the product UI.
  </p>

  <h2>Third parties we share data with</h2>
  <p>
    No analytics provider, email provider, payment processor,
    error-reporting service, or CDN is configured in this project. There is
    no bank aggregator configured.
    Expense and budget data submitted to the API is stored in the
    configured PostgreSQL database; the hosting arrangement is not
    specified here.
  </p>
  <p>Hosting arrangement: <code>{LEGAL.hosting}</code>.</p>

  <h2>How long we keep data</h2>
  <p>
    No retention period or automatic deletion schedule for expense records
    is defined in this project. An authenticated owner can delete an
    individual expense through the API, but there is no account-deletion
    flow. The same is true of budgets: an authenticated owner can delete an
    individual budget through the API. Records remain in the database until
    an owner deletes them, they are removed through another authorized
    means, or the database itself is deleted; the user foreign key is
    configured to cascade if an account is deleted through Django.
  </p>

  <h2>Your rights</h2>
  <p>
    Readers of a privacy page are typically entitled to rights such as access,
    rectification, erasure, restriction, portability, objection, and the
    ability to complain to a supervisory authority. The authenticated API
    and website let an owner list, edit, and delete their own expenses and
    budgets, which covers access, rectification, and erasure for that data.
    There is no data export feature and no account-deletion feature — an
    owner can delete each of their records individually, but not their
    account itself. Whether a deployment holds records about you depends on
    its use and database state; contact the operator to ask about a
    specific record or request.
  </p>
  <p>
    To ask a question or exercise any of these rights, the contact route is:
    <code>{LEGAL.contact}</code>. Which legal regime applies is not yet
    settled: <code>{LEGAL.jurisdiction}</code>.
  </p>

  <h2>How we protect data</h2>
  <p>
    Your password is never stored as plain text: Cashmire uses Django's
    built-in password hashing (its default algorithm, PBKDF2) to store a
    salted hash, not the password itself. Logging in sets an
    <code>HttpOnly</code> session cookie, so page JavaScript cannot read it
    even if a scripting bug existed. The login endpoint is rate-limited to
    5 attempts per minute per IP address to slow down password-guessing.
  </p>
  <p>
    Expense and budget endpoints require an authenticated Django session and
    scope records to that session's user — one account can never read,
    edit, or delete another account's data. Creation assigns each record to
    the requesting user, and writes only accept categories owned by that
    user. Django/DRF session authentication applies CSRF checks, using the
    <code>csrftoken</code> cookie described above, to every state-changing
    authenticated request. These application checks do not amount to a
    production security guarantee.
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
    hardened production security posture; the project should not be treated
    as production-ready or used with real financial data without appropriate
    operational hardening.
  </p>
  <p>
    To be explicit about what this page does not claim: it does not say that
    data is encrypted at rest; it does not say that traffic is served over
    TLS or HTTPS; or that access to data is audited or protected by a
    production access-control policy. These limitations are not security
    guarantees.
  </p>

  <h2>What is planned, and not yet built</h2>
  <p>
    Account registration, login, logout, expense tracking, and budget
    tracking — including their website forms — are implemented today, not
    merely planned; the sections above describe what they actually do.
    Still not implemented: account deletion, a way to export your own data,
    password reset ("forgot password"), and email verification. This page
    must be updated as those features become available and their actual
    data handling is known.
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
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
    line-height: 1.5;
  }

  .draft-banner {
    border: 2px solid var(--color-warning-border);
    background: var(--color-warning-bg);
    color: var(--color-warning-text);
    padding: var(--space-md) var(--space-lg);
    border-radius: var(--radius-md);
  }

  a {
    color: var(--color-primary);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }

  code {
    font-size: 0.95em;
  }
</style>
