<script>
  // API health check screen — see docs/specs/issue-18-health-screen.md.
  //
  // Fetches GET /api/health/ from onMount (not a `load` function — §4.6 of
  // the spec explains why: a `load` function cannot express the in-flight
  // "loading" state inside this page, and would route failures through
  // SvelteKit's error boundary instead of this component's error state).
  import { onMount } from "svelte";
  import { CircleCheck, CircleX } from "@lucide/svelte";

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
        let message = `L'API a répondu avec HTTP ${response.status} ${response.statusText} à l'adresse ${requestUrl}.`;
        if (response.status === 404) {
          message += ` Le point de terminaison de santé se trouve à /api/health/. Vérifiez que VITE_API_URL pointe vers l'API Cashmire et n'inclut pas déjà le préfixe /api.`;
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
        errorMessage = `L'API à ${requestUrl} a renvoyé HTTP ${response.status} mais le corps de la réponse n'a pas pu être lu comme du JSON.`;
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
        errorMessage = `L'API à ${requestUrl} a renvoyé HTTP ${response.status} mais le corps de la réponse ne contenait pas de champ status.`;
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
        errorMessage = `L'API à ${requestUrl} n'a pas répondu dans un délai de ${TIMEOUT_MS / 1000} secondes.`;
      } else {
        errorMessage = `Impossible de joindre l'API à ${requestUrl}. La requête ne s'est jamais terminée — il se peut que l'API ne soit pas démarrée, que l'URL soit incorrecte, ou que l'origine du navigateur ne soit pas autorisée par la configuration CORS de l'API.`;
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
  <title>État de l'API · Cashmire</title>
  <meta
    name="description"
    content="Vérifie si l'API Cashmire est accessible et affiche ce qu'elle a renvoyé."
  />
</svelte:head>

<main>
  <h1>Contrôle de l'état de l'API</h1>
  <p>
    Cette page interroge le point de terminaison de santé de l'API Cashmire
    et affiche la réponse obtenue.
  </p>

  <div class="state-region" role="status">
    {#if uiState === "loading"}
      <p class="state state-loading">
        <span class="spinner" aria-hidden="true"></span>
        Interrogation de l'API…
      </p>
      <p class="url-line">Appel de <code>{requestUrl}</code></p>
    {:else if uiState === "success"}
      <p class="state state-success">
        <CircleCheck size={18} />
        <strong>L'API est accessible</strong>
      </p>
      <p>Statut signalé : {health.status}</p>
      <p>HTTP {httpStatus}</p>
      <p class="url-line">URL appelée : <code>{requestUrl}</code></p>
      <p class="caveat">
        Cela confirme que l'API a répondu ; cela ne vérifie ni la base de
        données, ni aucun autre sous-système.
      </p>
      <pre>{JSON.stringify(health, null, 2)}</pre>
    {:else if uiState === "error"}
      <p class="state state-error">
        <CircleX size={18} />
        <strong>Échec du contrôle de l'API</strong>
      </p>
      <p>{errorMessage}</p>
      <p class="url-line">URL appelée : <code>{requestUrl}</code></p>
      <p>
        {#if httpStatus !== null}
          HTTP {httpStatus}
        {:else}
          Aucune réponse reçue.
        {/if}
      </p>
      <button type="button" onclick={retry}>Réessayer</button>
    {/if}
  </div>

  <p><a href="/">Retour à la page d'accueil de Cashmire</a></p>
</main>

<style>
  /* Adopted onto the shared tokens (issue #104) — previously hardcoded hex,
     the one screen decision 0001's amendment for #104 did not reach. */
  main {
    max-width: 70ch;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
    line-height: var(--line-height-body);
  }

  .state-region {
    margin: var(--space-2xl) 0;
    padding: var(--space-lg) var(--space-xl);
    border-radius: var(--radius-md);
    overflow-wrap: anywhere;
  }

  .state-loading,
  .state-success,
  .state-error {
    display: flex;
    align-items: center;
    gap: var(--space-xs);
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--radius-sm);
  }

  .state-loading :global(svg),
  .state-success :global(svg),
  .state-error :global(svg) {
    flex-shrink: 0;
  }

  .state-loading {
    color: var(--color-text-muted);
    background: var(--color-oatmeal);
    border-left: 4px solid var(--color-border-subtle);
  }

  .state-success {
    color: var(--color-success-text);
    background: var(--color-success-bg);
    border-left: 4px solid var(--color-success-border);
  }

  .state-error {
    color: var(--color-error-text);
    background: var(--color-error-bg);
    border-left: 4px solid var(--color-error-border);
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
    background: var(--color-oatmeal);
    padding: var(--space-md);
    border-radius: var(--radius-sm);
  }

  button {
    font-family: var(--font-body);
    font-size: var(--font-size-base);
    font-weight: 500;
    padding: var(--space-sm) var(--space-xl);
    border-radius: var(--radius-full);
    border: 1px solid var(--color-cta-bg);
    background: var(--color-cta-bg);
    color: var(--color-cta-text);
    cursor: pointer;
    transition: background-color var(--motion-duration) var(--motion-ease);
  }

  button:hover {
    background: var(--color-mocha);
    border-color: var(--color-mocha);
  }

  .spinner {
    display: inline-block;
    width: 0.9em;
    height: 0.9em;
    border: 2px solid var(--color-border-subtle);
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
