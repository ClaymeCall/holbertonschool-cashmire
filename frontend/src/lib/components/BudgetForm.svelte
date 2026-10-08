<script>
  // Shared budget create/edit form — issue #53 explicitly asks for one
  // form "reused for both create and edit flows", unlike expenses (#40/#41)
  // where create/edit stayed two separate screens. The two routes
  // (`routes/budgets/new`, `routes/budgets/[id]/edit`) each own loading
  // their own data and calling create/update; this component only renders
  // the fields and does client-side validation.
  //
  // `category_id`/`period_start`/`period_end` are only accepted by the
  // create route per `docs/api-design.md` §4.4 ("généralement non
  // modifiables après création") — in edit mode the category and month are
  // shown read-only rather than as editable controls.
  import { ApiError } from "$lib/api";
  import { isValidDecimalString, compareDecimal } from "$lib/money";
  import Button from "$lib/components/Button.svelte";
  import TextField from "$lib/components/TextField.svelte";
  import FormError from "$lib/components/FormError.svelte";

  /**
   * @typedef {Object} Props
   * @property {"create" | "edit"} mode
   * @property {Array<{ id: number, name: string }>} categories
   * @property {string} [initialCategoryId]
   * @property {string} [initialMonth] `"YYYY-MM"`
   * @property {string} [initialAmount]
   * @property {string} [initialAlertThreshold]
   * @property {string} submitLabel
   * @property {(values: { category_id: number, month: string, amount: string, alert_threshold: string }) => Promise<void>} onsubmit
   *   Called with the validated values; the caller shapes the actual API
   *   payload (create sends category_id/month/amount/alert_threshold, edit
   *   sends only amount/alert_threshold) and re-throws on failure for this
   *   component to render.
   */

  /** @type {Props} */
  let {
    mode,
    categories,
    initialCategoryId = "",
    initialMonth = "",
    initialAmount = "",
    initialAlertThreshold = "80.00",
    submitLabel,
    onsubmit,
  } = $props();

  let categoryId = $state(initialCategoryId || String(categories[0]?.id ?? ""));
  let month = $state(initialMonth);
  let amount = $state(initialAmount);
  let alertThreshold = $state(initialAlertThreshold);

  /** @typedef {"idle" | "submitting" | "error"} FormState */
  /** @type {FormState} */
  let formState = $state("idle");
  /** @type {string[]} */
  let errorMessages = $state([]);

  function clientValidationErrors() {
    const errors = [];
    if (!categoryId) errors.push("Choose a category.");
    if (!month) errors.push("Choose a month.");
    if (!isValidDecimalString(amount.trim()) || compareDecimal(amount.trim(), "0") <= 0) {
      errors.push("Enter a limit greater than 0 (e.g. 500.00).");
    }
    const threshold = alertThreshold.trim();
    if (
      !isValidDecimalString(threshold) ||
      compareDecimal(threshold, "0") < 0 ||
      compareDecimal(threshold, "100") > 0
    ) {
      errors.push("The alert threshold must be between 0 and 100.");
    }
    return errors;
  }

  /**
   * DRF's default validation-error shape is `{ field: ["message", ...] }`;
   * the documented application-error envelope (409 conflict) is
   * `{ error, message }`.
   * @param {unknown} body
   * @returns {string[] | null}
   */
  function flattenFieldErrors(body) {
    if (!body || typeof body !== "object" || Array.isArray(body)) return null;
    if (typeof body.message === "string") return [body.message];
    const messages = [];
    for (const value of Object.values(body)) {
      if (Array.isArray(value)) {
        messages.push(...value.map(String));
      } else if (typeof value === "string") {
        messages.push(value);
      }
    }
    return messages.length > 0 ? messages : null;
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
      await onsubmit({
        category_id: Number(categoryId),
        month,
        amount: amount.trim(),
        alert_threshold: alertThreshold.trim(),
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // #53 AC: the duplicate-budget conflict must be surfaced clearly,
        // not folded into a generic failure message.
        errorMessages = flattenFieldErrors(err.body) ?? [
          "A budget for this category and month already exists.",
        ];
      } else if (err instanceof ApiError && err.status === 400) {
        errorMessages = flattenFieldErrors(err.body) ?? [
          "Check the highlighted fields and try again.",
        ];
      } else if (err instanceof ApiError && err.status === 401) {
        errorMessages = ["You need to be logged in to manage budgets."];
      } else if (err instanceof ApiError && err.status === 403) {
        errorMessages = ["This request couldn't be verified. Refresh the page and try again."];
      } else if (err instanceof ApiError && err.status === 404) {
        errorMessages = ["That category couldn't be found. Refresh and try again."];
      } else {
        errorMessages = ["Couldn't reach Cashmire. Try again in a moment."];
      }
      formState = "error";
      console.error("Failed to save budget:", err);
    }
  }
</script>

<form onsubmit={handleSubmit} novalidate>
  {#if mode === "create"}
    <div class="field">
      <label for="budget-category">Category</label>
      <select
        id="budget-category"
        bind:value={categoryId}
        disabled={formState === "submitting" || categories.length === 0}
        required
      >
        {#each categories as category (category.id)}
          <option value={String(category.id)}>{category.name}</option>
        {/each}
      </select>
    </div>

    <TextField
      id="budget-month"
      name="month"
      label="Month"
      type="month"
      bind:value={month}
      disabled={formState === "submitting"}
      required
    />
  {:else}
    <p class="readonly-field">
      <span class="readonly-label">Category</span>
      {categories.find((c) => String(c.id) === categoryId)?.name ?? "—"}
    </p>
    <p class="readonly-field">
      <span class="readonly-label">Month</span>
      {month}
    </p>
  {/if}

  <TextField
    id="budget-amount"
    name="amount"
    label="Limit"
    type="text"
    inputmode="decimal"
    placeholder="500.00"
    bind:value={amount}
    disabled={formState === "submitting"}
    required
  />

  <TextField
    id="budget-alert-threshold"
    name="alert_threshold"
    label="Alert threshold (%)"
    type="text"
    inputmode="decimal"
    hint="Warn when spending reaches this percentage. Defaults to 80."
    bind:value={alertThreshold}
    disabled={formState === "submitting"}
  />

  {#if formState === "error"}
    <FormError messages={errorMessages} />
  {/if}

  <Button type="submit" disabled={formState === "submitting"}>
    {formState === "submitting" ? "Saving…" : submitLabel}
  </Button>
</form>

<style>
  .field {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    margin-bottom: var(--space-lg);
  }

  label {
    font-weight: 600;
  }

  select {
    font-size: var(--font-size-base);
    padding: var(--space-sm) 0.6rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
  }

  select:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 1px;
  }

  .readonly-field {
    margin: 0 0 var(--space-lg);
  }

  .readonly-label {
    display: block;
    font-weight: 600;
  }
</style>
