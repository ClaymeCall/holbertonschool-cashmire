<script>
  // Registration screen — issue #28.
  //
  // Posts to POST /api/auth/register/ per docs/mvp-scope.md §3.1. The
  // backend does not implement that route yet (tracked in #22-#24), so
  // today every submission fails with a network/404-shaped error — this
  // page is still built against the documented contract so it works
  // unmodified once the backend ships.
  //
  // Password rule enforced client-side: minimum length 8, matching
  // docs/mvp-scope.md §3.1's "Django validators (longueur minimale, ...)".
  // The other Django validators (common-password, too-similar-to-user,
  // numeric-only) can only really be checked server-side against the live
  // user record, so AC-1 ("password rules") is satisfied here for the one
  // rule that is meaningfully client-side; the rest surface through AC-2's
  // server-side validation errors once the backend exists.
  import { goto } from "$app/navigation";
  import { UserPlus, LoaderCircle } from "@lucide/svelte";
  import { apiFetch, ApiError } from "$lib/api";
  import { setCurrentUser } from "$lib/auth.svelte.js";
  import Button from "$lib/components/Button.svelte";
  import TextField from "$lib/components/TextField.svelte";
  import FormError from "$lib/components/FormError.svelte";

  const MIN_PASSWORD_LENGTH = 8;
  const TIMEOUT_MS = 8000;

  /** @typedef {"idle" | "submitting" | "error"} FormState */

  let email = $state("");
  let password = $state("");
  let passwordConfirm = $state("");
  /** @type {FormState} */
  let formState = $state("idle");
  /** @type {string[]} */
  let errorMessages = $state([]);

  function clientValidationErrors() {
    /** @type {string[]} */
    const errors = [];
    if (email.trim() === "") {
      errors.push("Entrez votre adresse e-mail.");
    }
    if (password === "") {
      errors.push("Entrez un mot de passe.");
    } else if (password.length < MIN_PASSWORD_LENGTH) {
      errors.push(`Le mot de passe doit contenir au moins ${MIN_PASSWORD_LENGTH} caractères.`);
    }
    if (password !== "" && password === email.trim()) {
      errors.push("Le mot de passe ne doit pas être identique à votre e-mail.");
    }
    if (passwordConfirm !== password) {
      errors.push("Les mots de passe ne correspondent pas.");
    }
    return errors;
  }

  /**
   * Flattens a DRF-shaped validation error body ({ field: ["msg", ...] } or
   * { detail: "msg" }) into display strings. Falls back to a generic message
   * for any other shape, rather than rendering raw JSON to the user.
   * @param {unknown} body
   * @returns {string[]}
   */
  function messagesFromErrorBody(body) {
    if (body && typeof body === "object" && !Array.isArray(body)) {
      const messages = [];
      for (const [field, value] of Object.entries(body)) {
        const values = Array.isArray(value) ? value : [value];
        for (const v of values) {
          if (typeof v !== "string") continue;
          messages.push(field === "detail" ? v : `${field}: ${v}`);
        }
      }
      if (messages.length > 0) return messages;
    }
    return ["Impossible de créer le compte avec les informations fournies."];
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (formState === "submitting") return;

    const validationErrors = clientValidationErrors();
    if (validationErrors.length > 0) {
      errorMessages = validationErrors;
      formState = "error";
      return;
    }

    formState = "submitting";
    errorMessages = [];

    try {
      const createdUser = await apiFetch("/api/auth/register/", {
        method: "POST",
        body: { email: email.trim(), password },
        credentials: "include",
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      // Registration also establishes a session per docs/mvp-scope.md §3.1
      // ("inscription immédiate") — same redirect as a successful login.
      // The response body is already the created user (UserSerializer
      // shape), so the nav can reflect the logged-in state immediately
      // without a round trip to /api/auth/me/.
      setCurrentUser(/** @type {{ id: number, email: string }} */ (createdUser));
      await goto("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        // AC-2: surface the server's field-level validation errors.
        errorMessages = messagesFromErrorBody(err.body);
      } else if (
        err &&
        (err.name === "TimeoutError" || err.name === "AbortError")
      ) {
        errorMessages = ["La requête a expiré. Réessayez."];
      } else {
        errorMessages = ["Impossible de joindre Cashmire. Réessayez dans un instant."];
      }
      formState = "error";
      console.error("Registration failed:", err);
    }
  }
</script>

<svelte:head>
  <title>Inscription · Cashmire</title>
  <meta name="description" content="Créez votre compte Cashmire." />
</svelte:head>

<main>
  <h1>Inscription</h1>

  <form onsubmit={handleSubmit} novalidate>
    <TextField
      id="register-email"
      name="email"
      label="E-mail"
      type="email"
      autocomplete="email"
      bind:value={email}
      disabled={formState === "submitting"}
      required
    />

    <TextField
      id="register-password"
      name="password"
      label="Mot de passe"
      type="password"
      autocomplete="new-password"
      minlength={MIN_PASSWORD_LENGTH}
      bind:value={password}
      disabled={formState === "submitting"}
      required
      hint={`Au moins ${MIN_PASSWORD_LENGTH} caractères.`}
    />

    <TextField
      id="register-password-confirm"
      name="password_confirm"
      label="Confirmer le mot de passe"
      type="password"
      autocomplete="new-password"
      bind:value={passwordConfirm}
      disabled={formState === "submitting"}
      required
    />

    {#if formState === "error"}
      <FormError messages={errorMessages} />
    {/if}

    <Button type="submit" disabled={formState === "submitting"}>
      {#if formState === "submitting"}
        <LoaderCircle size={16} class="spin" /> Création du compte…
      {:else}
        <UserPlus size={16} /> Créer un compte
      {/if}
    </Button>
  </form>

  <p><a href="/login">Vous avez déjà un compte ? Connectez-vous</a></p>
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
