<script>
  // Login screen — issue #29.
  //
  // Posts to POST /api/auth/login/ per docs/mvp-scope.md §3.1. The backend
  // does not implement that route yet (tracked in #22-#24), so today every
  // submission fails with a network/404-shaped error — this page is still
  // built against the documented contract so it works unmodified once the
  // backend ships.
  //
  // Session strategy: docs/mvp-scope.md §3.1 says the API "establishes a
  // session" (no explicit token in the response to store). `apiFetch` is
  // called with `credentials: "include"` so the browser keeps whatever
  // session cookie the backend sets; there is nothing for this component to
  // store itself. Issue #25 (session/token strategy write-up) is still open
  // — if it lands on a different mechanism, this call site is the one place
  // to change.
  import { goto } from "$app/navigation";
  import { LogIn, LoaderCircle } from "@lucide/svelte";
  import { apiFetch, ApiError } from "$lib/api";
  import { setCurrentUser } from "$lib/auth.svelte.js";
  import Button from "$lib/components/Button.svelte";
  import TextField from "$lib/components/TextField.svelte";
  import FormError from "$lib/components/FormError.svelte";

  /** @typedef {"idle" | "submitting" | "error"} FormState */

  const TIMEOUT_MS = 8000;

  let email = $state("");
  let password = $state("");
  /** @type {FormState} */
  let formState = $state("idle");
  /** @type {string | null} */
  let errorMessage = $state(null);

  function clientValidationError() {
    if (email.trim() === "" || password === "") {
      return "Entrez votre e-mail et votre mot de passe.";
    }
    return null;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (formState === "submitting") return;

    const validationError = clientValidationError();
    if (validationError) {
      errorMessage = validationError;
      formState = "error";
      return;
    }

    formState = "submitting";
    errorMessage = null;

    try {
      const loggedInUser = await apiFetch("/api/auth/login/", {
        method: "POST",
        body: { email: email.trim(), password },
        credentials: "include",
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      // Successful login: the server has set a session cookie, and the
      // response body is already the logged-in user (UserSerializer
      // shape) — feed it straight into the nav's auth state (AC-3).
      setCurrentUser(/** @type {{ id: number, email: string }} */ (loggedInUser));
      await goto("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // Clear, non-technical message (AC-2) — never echo the server's
        // own wording, which could leak whether the email exists.
        errorMessage = "E-mail ou mot de passe incorrect.";
      } else if (err instanceof ApiError && err.status === 400) {
        errorMessage = "Entrez votre e-mail et votre mot de passe.";
      } else if (
        err &&
        (err.name === "TimeoutError" || err.name === "AbortError")
      ) {
        errorMessage = "La requête a expiré. Réessayez.";
      } else {
        // Network failure, CORS rejection, 5xx, or the route not existing
        // yet (ApiError with status 0 or a non-2xx the two branches above
        // don't cover) — one generic message, no internal detail leaked.
        errorMessage = "Impossible de joindre Cashmire. Réessayez dans un instant.";
      }
      formState = "error";
      console.error("Login failed:", err);
    }
  }
</script>

<svelte:head>
  <title>Connexion · Cashmire</title>
  <meta name="description" content="Connectez-vous à votre compte Cashmire." />
</svelte:head>

<main>
  <h1>Connexion</h1>

  <form onsubmit={handleSubmit} novalidate>
    <TextField
      id="login-email"
      name="email"
      label="E-mail"
      type="email"
      autocomplete="email"
      bind:value={email}
      disabled={formState === "submitting"}
      required
    />

    <TextField
      id="login-password"
      name="password"
      label="Mot de passe"
      type="password"
      autocomplete="current-password"
      bind:value={password}
      disabled={formState === "submitting"}
      required
    />

    {#if formState === "error"}
      <FormError messages={errorMessage ? [errorMessage] : []} />
    {/if}

    <Button type="submit" disabled={formState === "submitting"}>
      {#if formState === "submitting"}
        <LoaderCircle size={16} class="spin" /> Connexion…
      {:else}
        <LogIn size={16} /> Se connecter
      {/if}
    </Button>
  </form>

  <p><a href="/register">Besoin d'un compte ? Inscrivez-vous</a></p>
  <p><a href="/">Retour à la page d'accueil de Cashmire</a></p>
</main>

<style>
  main {
    max-width: 40ch;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
    line-height: 1.5;
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }

  a {
    color: var(--color-primary);
  }

  /* `:global` because the LoaderCircle icon's <svg> is rendered inside
     @lucide/svelte's own Icon.svelte, not this component's template — a
     plain `.spin` rule here would never match it (Svelte's style scoping
     only tags elements written directly in this file). Respects
     prefers-reduced-motion via base.css's blanket
     `animation-duration: 0.01ms !important` rule. */
  :global(.spin) {
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
