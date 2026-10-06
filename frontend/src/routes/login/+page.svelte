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
  import { apiFetch, ApiError } from "$lib/api";

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
      return "Enter your email and password.";
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
      await apiFetch("/api/auth/login/", {
        method: "POST",
        body: { email: email.trim(), password },
        credentials: "include",
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      // Successful login: the server has set a session cookie. Nothing to
      // store client-side — redirect into the app shell (AC-3).
      await goto("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // Clear, non-technical message (AC-2) — never echo the server's
        // own wording, which could leak whether the email exists.
        errorMessage = "Incorrect email or password.";
      } else if (err instanceof ApiError && err.status === 400) {
        errorMessage = "Enter your email and password.";
      } else if (
        err &&
        (err.name === "TimeoutError" || err.name === "AbortError")
      ) {
        errorMessage = "The request timed out. Try again.";
      } else {
        // Network failure, CORS rejection, 5xx, or the route not existing
        // yet (ApiError with status 0 or a non-2xx the two branches above
        // don't cover) — one generic message, no internal detail leaked.
        errorMessage = "Couldn't reach Cashmire. Try again in a moment.";
      }
      formState = "error";
      console.error("Login failed:", err);
    }
  }
</script>

<svelte:head>
  <title>Log in · Cashmire</title>
  <meta name="description" content="Sign in to your Cashmire account." />
</svelte:head>

<main>
  <h1>Log in</h1>

  <form onsubmit={handleSubmit} novalidate>
    <div class="field">
      <label for="login-email">Email</label>
      <input
        id="login-email"
        name="email"
        type="email"
        autocomplete="email"
        bind:value={email}
        disabled={formState === "submitting"}
        required
      />
    </div>

    <div class="field">
      <label for="login-password">Password</label>
      <input
        id="login-password"
        name="password"
        type="password"
        autocomplete="current-password"
        bind:value={password}
        disabled={formState === "submitting"}
        required
      />
    </div>

    {#if formState === "error" && errorMessage}
      <p class="error" role="alert">{errorMessage}</p>
    {/if}

    <button type="submit" disabled={formState === "submitting"}>
      {formState === "submitting" ? "Logging in…" : "Log in"}
    </button>
  </form>

  <p><a href="/register">Need an account? Register</a></p>
  <p><a href="/">Back to the Cashmire home page</a></p>
</main>

<style>
  main {
    max-width: 40ch;
    margin: 0 auto;
    padding: 1.5rem 1.25rem 3rem;
    line-height: 1.5;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 1rem;
  }

  label {
    font-weight: 600;
  }

  input {
    font-size: 1rem;
    padding: 0.5rem 0.6rem;
    border: 1px solid #8a8a8a;
    border-radius: 4px;
  }

  input:focus-visible {
    outline: 3px solid #0b3d91;
    outline-offset: 1px;
  }

  .error {
    color: #7a0a0a;
    background: #fdeaea;
    border-left: 4px solid #b00020;
    padding: 0.5rem 0.75rem;
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
</style>
