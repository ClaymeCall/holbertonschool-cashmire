<script>
  // Registration screen — issue #28. The API returns the same neutral 202
  // response for new and existing accounts to prevent email enumeration;
  // users sign in separately after submitting the form (issue #146).
  import { UserPlus, LoaderCircle } from "@lucide/svelte";
  import { apiFetch, ApiError } from "$lib/api";
  import Button from "$lib/components/Button.svelte";
  import TextField from "$lib/components/TextField.svelte";
  import FormError from "$lib/components/FormError.svelte";

  const MIN_PASSWORD_LENGTH = 8;
  const TIMEOUT_MS = 8000;

  /** @typedef {"idle" | "submitting" | "error" | "success"} FormState */

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
      errors.push("Enter your email address.");
    }
    if (password === "") {
      errors.push("Enter a password.");
    } else if (password.length < MIN_PASSWORD_LENGTH) {
      errors.push(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
    }
    if (password !== "" && password === email.trim()) {
      errors.push("Password must not be the same as your email.");
    }
    if (passwordConfirm !== password) {
      errors.push("Passwords do not match.");
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
    return ["Couldn't create the account with the details provided."];
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
      await apiFetch("/api/auth/register/", {
        method: "POST",
        body: { email: email.trim(), password },
        credentials: "include",
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      formState = "success";
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        // AC-2: surface the server's field-level validation errors.
        errorMessages = messagesFromErrorBody(err.body);
      } else if (err instanceof ApiError && err.status === 429) {
        errorMessages = ["Too many registration attempts. Wait a minute, then try again."];
      } else if (
        err &&
        (err.name === "TimeoutError" || err.name === "AbortError")
      ) {
        errorMessages = ["The request timed out. Try again."];
      } else {
        errorMessages = ["Couldn't reach Cashmire. Try again in a moment."];
      }
      formState = "error";
      console.error("Registration failed:", err);
    }
  }
</script>

<svelte:head>
  <title>Register · Cashmire</title>
  <meta name="description" content="Create a Cashmire account." />
</svelte:head>

<main>
  <h1>Register</h1>

  {#if formState === "success"}
    <p role="status">
      If registration can be completed, you can now sign in. If you already
      have an account, sign in to continue.
    </p>
    <p><a href="/login">Go to sign in</a></p>
  {:else}
    <form onsubmit={handleSubmit} novalidate>
      <TextField
        id="register-email"
        name="email"
        label="Email"
        type="email"
        autocomplete="email"
        bind:value={email}
        disabled={formState === "submitting"}
        required
      />

      <TextField
        id="register-password"
        name="password"
        label="Password"
        type="password"
        autocomplete="new-password"
        minlength={MIN_PASSWORD_LENGTH}
        bind:value={password}
        disabled={formState === "submitting"}
        required
        hint={`At least ${MIN_PASSWORD_LENGTH} characters.`}
      />

      <TextField
        id="register-password-confirm"
        name="password_confirm"
        label="Confirm password"
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
          <LoaderCircle size={16} class="spin" /> Creating account…
        {:else}
          <UserPlus size={16} /> Create account
        {/if}
      </Button>
    </form>
  {/if}

  <p><a href="/login">Already have an account? Log in</a></p>
  <p><a href="/">Back to the Cashmire home page</a></p>
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
