<script>
  // Edit-expense screen — issue #41.
  //
  // `backend/api/urls.py` has no `GET /api/expenses/{id}/` (only PATCH/PUT/
  // DELETE on the detail route — see `backend/api/views.py`'s
  // `expense_detail_mutation`), so there is nothing to fetch a single
  // expense from. The MVP has no pagination (`docs/api-design.md` §1.7:
  // "Toutes les listes ... retournent l'ensemble complet"), so refetching
  // the full list and finding this id in it is the one call the backend
  // actually supports, not a workaround.
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { ApiError } from "$lib/api";
  import { listExpenses, updateExpense } from "$lib/api/expenses";
  import { listCategories } from "$lib/api/categories";
  import { isValidDecimalString, compareDecimal } from "$lib/money";
  import Button from "$lib/components/Button.svelte";
  import TextField from "$lib/components/TextField.svelte";
  import FormError from "$lib/components/FormError.svelte";

  /** @typedef {"loading" | "idle" | "submitting" | "error" | "not-found"} FormState */

  const expenseId = Number($page.params.id);

  /** @type {FormState} */
  let formState = $state("loading");
  /** @type {Array<{ id: number, name: string }>} */
  let categories = $state([]);
  /** @type {string[]} */
  let errorMessages = $state([]);

  let categoryId = $state("");
  let amount = $state("");
  let description = $state("");
  let date = $state("");

  onMount(async () => {
    try {
      const [categoryList, expenses] = await Promise.all([
        listCategories(),
        listExpenses(),
      ]);
      categories = categoryList;

      const expense = expenses.find((e) => e.id === expenseId);
      if (!expense) {
        formState = "not-found";
        return;
      }

      categoryId = String(expense.category_id);
      amount = expense.amount;
      description = expense.description ?? "";
      date = expense.date;
      formState = "idle";
    } catch (err) {
      errorMessages = ["Couldn't load this expense. Try again in a moment."];
      formState = "error";
      console.error("Failed to load expense:", err);
    }
  });

  function clientValidationErrors() {
    const errors = [];
    if (!categoryId) errors.push("Choose a category.");
    if (!isValidDecimalString(amount.trim()) || compareDecimal(amount.trim(), "0") <= 0) {
      errors.push("Enter an amount greater than 0 (e.g. 12.50).");
    }
    if (!date) errors.push("Choose a date.");
    return errors;
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
      await updateExpense(expenseId, {
        category_id: Number(categoryId),
        amount: amount.trim(),
        description: description.trim() === "" ? null : description.trim(),
        date,
      });
      await goto("/expenses");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        errorMessages = flattenFieldErrors(err.body) ?? [
          "Check the highlighted fields and try again.",
        ];
      } else if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        errorMessages = ["You need to be logged in to edit an expense."];
      } else if (err instanceof ApiError && err.status === 404) {
        errorMessages = ["This expense or category couldn't be found."];
      } else {
        errorMessages = ["Couldn't reach Cashmire. Try again in a moment."];
      }
      formState = "error";
      console.error("Failed to update expense:", err);
    }
  }

  /**
   * @param {unknown} body
   * @returns {string[] | null}
   */
  function flattenFieldErrors(body) {
    if (!body || typeof body !== "object" || Array.isArray(body)) return null;
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
</script>

<svelte:head>
  <title>Edit expense · Cashmire</title>
  <meta name="description" content="Edit an existing expense." />
</svelte:head>

<main>
  <h1>Edit expense</h1>

  {#if formState === "loading"}
    <p role="status">Loading…</p>
  {:else if formState === "not-found"}
    <p>That expense couldn't be found.</p>
  {:else}
    <form onsubmit={handleSubmit} novalidate>
      <div class="field">
        <label for="expense-category">Category</label>
        <select
          id="expense-category"
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
        id="expense-amount"
        name="amount"
        label="Amount"
        type="text"
        inputmode="decimal"
        placeholder="12.50"
        bind:value={amount}
        disabled={formState === "submitting"}
        required
      />

      <TextField
        id="expense-date"
        name="date"
        label="Date"
        type="date"
        bind:value={date}
        disabled={formState === "submitting"}
        required
      />

      <TextField
        id="expense-description"
        name="description"
        label="Description"
        hint="Optional"
        bind:value={description}
        disabled={formState === "submitting"}
      />

      {#if formState === "error"}
        <FormError messages={errorMessages} />
      {/if}

      <Button type="submit" disabled={formState === "submitting"}>
        {formState === "submitting" ? "Saving…" : "Save changes"}
      </Button>
    </form>
  {/if}

  <p><a href="/expenses">Back to expenses</a></p>
</main>

<style>
  main {
    max-width: 40ch;
    margin: 0 auto;
    padding: var(--space-2xl) var(--space-xl) var(--space-3xl);
    line-height: 1.5;
  }

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

  a {
    color: var(--color-primary);
  }

  a:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
