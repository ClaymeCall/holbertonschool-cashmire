<script>
  // API health check screen — see docs/specs/issue-18-health-screen.md.
  //
  // Fetches GET /api/health/ from onMount (not a `load` function — §4.6 of
  // the spec explains why: a `load` function cannot express the in-flight
  // "loading" state inside this page, and would route failures through
  // SvelteKit's error boundary instead of this component's error state).
  import { onMount } from "svelte";

  /**
   * Body returned by GET /api/health/.
   * The backend returns exactly {"status": "ok"} today
   * (backend/api/views.py). `status` is typed as string, not the literal "ok",
   * because the screen must render whatever value arrives rather than assume it.
   * @typedef {{ status: string }} HealthResponse
   */

  /**
   * @typedef {"loading" | "success" | "error"} HealthState
   */

  // §4.5: read import.meta.env.VITE_API_URL, treating a missing or blank
  // value as absent, and strip a trailing slash from the base before
  // concatenating `/api/health/` (which keeps its own trailing slash so
  // Django's APPEND_SLASH does not force a cross-origin redirect).
  // Computed inside the component's script block (not module scope) so each
  // instance re-reads the env var, which is what lets tests stub it per-case.
  const rawApiUrl = import.meta.env.VITE_API_URL;
  const apiBase =
    rawApiUrl && rawApiUrl.trim()
      ? rawApiUrl.trim().replace(/\/+$/, "")
      : "http://localhost:8000";
  const requestUrl = `${apiBase}/api/health/`;

  // §6.3: abort a request that never settles after 8 seconds, so the page
  // does not stay stuck on "Checking…" forever (AC-8).
  const TIMEOUT_MS = 8000;

  /** @type {HealthState} */
  let uiState = $state("loading");
  /** @type {HealthResponse | null} */
  let health = $state(null);
  /** @type {number | null} */
  let httpStatus = $state(null);
  /** @type {string | null} */
  let errorMessage = $state(null);

  async function checkHealth() {
    uiState = "loading";
    health = null;
    httpStatus = null;
    errorMessage = null;

    try {
      const response = await fetch(requestUrl, {
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });

      if (!response.ok) {
        // §6.2 — a response arrived but response.ok is false.
        httpStatus = response.status;
        let message = `The API responded with HTTP ${response.status} ${response.statusText} at ${requestUrl}.`;
        if (response.status === 404) {
          message += ` The health endpoint is at /api/health/. Check that VITE_API_URL points at the Cashmire API and does not already include the /api prefix.`;
        }
        errorMessage = message;
        uiState = "error";
        return;
      }

      // §6.4 — the body may not be valid JSON, or may not have the
      // expected shape, even on a 2xx response.
      let body;
      try {
        body = await response.json();
      } catch {
        httpStatus = response.status;
        errorMessage = `The API at ${requestUrl} returned HTTP ${response.status} but the response body could not be read as JSON.`;
        uiState = "error";
        return;
      }

      if (
        body === null ||
        typeof body !== "object" ||
        Array.isArray(body) ||
        typeof body.status !== "string"
      ) {
        httpStatus = response.status;
        errorMessage = `The API at ${requestUrl} returned HTTP ${response.status} but the response body did not contain a status field.`;
        uiState = "error";
        return;
      }

      health = body;
      httpStatus = response.status;
      uiState = "success";
    } catch (err) {
      // §6.1 / §6.3 — the fetch promise rejected: no response at all. This
      // covers the API being down, DNS/connection failure, a CORS rejection
      // (browser gives JS no status code and no body for that case by
      // design), and an aborted request.
      if (err && (err.name === "TimeoutError" || err.name === "AbortError")) {
        errorMessage = `The API at ${requestUrl} did not respond within ${TIMEOUT_MS / 1000} seconds.`;
      } else {
        errorMessage = `Could not reach the API at ${requestUrl}. The request never completed — the API may not be running, the URL may be wrong, or the browser origin may not be allowed by the API's CORS configuration.`;
      }
      httpStatus = null;
      uiState = "error";
      // Console logging in addition to the UI is fine; the UI message above
      // does not depend on it. Logged once, here, per §6.5.
      console.error("Health check failed:", err);
    }
  }

  function retry() {
    if (uiState === "loading") return;
    checkHealth();
  }

  onMount(() => {
    checkHealth();
  });
</script>

<svelte:head>
  <title>API health · Cashmire</title>
  <meta
    name="description"
    content="Checks whether the Cashmire API is reachable and reports what it returned."
  />
</svelte:head>

<main>
  <h1>API health check</h1>
  <p>
    This page calls the Cashmire API's health endpoint and reports what came
    back.
  </p>

  <div class="state-region" role="status">
    {#if uiState === "loading"}
      <p class="state state-loading">
        <span class="spinner" aria-hidden="true"></span>
        Checking the API…
      </p>
      <p class="url-line">Calling <code>{requestUrl}</code></p>
    {:else if uiState === "success"}
      <p class="state state-success">
        <span class="glyph" aria-hidden="true">✓</span>
        <strong>API is reachable</strong>
      </p>
      <p>Reported status: {health.status}</p>
      <p>HTTP {httpStatus}</p>
      <p class="url-line">Called <code>{requestUrl}</code></p>
      <p class="caveat">
        This confirms the API answered; it does not check the database or any
        other subsystem.
      </p>
      <pre>{JSON.stringify(health, null, 2)}</pre>
    {:else if uiState === "error"}
      <p class="state state-error">
        <span class="glyph" aria-hidden="true">✕</span>
        <strong>API check failed</strong>
      </p>
      <p>{errorMessage}</p>
      <p class="url-line">Called <code>{requestUrl}</code></p>
      <p>
        {#if httpStatus !== null}
          HTTP {httpStatus}
        {:else}
          No response received.
        {/if}
      </p>
      <button type="button" onclick={retry}>Retry</button>
    {/if}
  </div>

  <p><a href="/">Back to the Cashmire home page</a></p>
</main>

<style>
  main {
    max-width: 70ch;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
    line-height: 1.5;
  }

  .state-region {
    margin: 1.5rem 0;
    padding: 1rem 1.25rem;
    border-radius: 4px;
    overflow-wrap: anywhere;
  }

  .state-loading {
    color: #3a3a3a;
    background: #f1f1f1;
    border-left: 4px solid #8a8a8a;
    padding: 0.5rem 0.75rem;
  }

  .state-success {
    color: #0b4d1e;
    background: #e6f4ea;
    border-left: 4px solid #1a7f37;
    padding: 0.5rem 0.75rem;
  }

  .state-error {
    color: #7a0a0a;
    background: #fdeaea;
    border-left: 4px solid #b00020;
    padding: 0.5rem 0.75rem;
  }

  .url-line code {
    overflow-wrap: anywhere;
  }

  .caveat {
    font-style: italic;
    font-size: 0.9em;
  }

  pre {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    background: #f5f5f5;
    padding: 0.75rem;
    border-radius: 4px;
  }

  button {
    font-size: 1rem;
    padding: 0.5rem 1rem;
    cursor: pointer;
  }

  button:focus-visible,
  a:focus-visible {
    outline: 3px solid #0b3d91;
    outline-offset: 2px;
  }

  a {
    color: #0b3d91;
  }

  .spinner {
    display: inline-block;
    width: 0.9em;
    height: 0.9em;
    border: 2px solid #8a8a8a;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    vertical-align: middle;
    margin-right: 0.35em;
  }

  @media (prefers-reduced-motion: reduce) {
    .spinner {
      animation: none;
    }
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
