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
      errorMessages = ["Impossible de charger cette dépense. Réessayez dans un instant."];
      formState = "error";
      console.error("Failed to load expense:", err);
    }
  });

  function clientValidationErrors() {
    const errors = [];
    if (!categoryId) errors.push("Choisissez une catégorie.");
    if (!isValidDecimalString(amount.trim()) || compareDecimal(amount.trim(), "0") <= 0) {
      errors.push("Saisissez un montant supérieur à 0 (ex. 12.50).");
    }
    if (!date) errors.push("Choisissez une date.");
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
          "Vérifiez les champs signalés et réessayez.",
        ];
      } else if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        errorMessages = ["Vous devez être connecté(e) pour modifier une dépense."];
      } else if (err instanceof ApiError && err.status === 404) {
        errorMessages = ["Cette dépense ou cette catégorie est introuvable."];
      } else {
        errorMessages = ["Impossible de joindre Cashmire. Réessayez dans un instant."];
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
  <title>Modifier la dépense · Cashmire</title>
  <meta name="description" content="Modifiez une dépense existante." />
</svelte:head>

<main>
  <h1>Modifier la dépense</h1>

  {#if formState === "loading"}
    <p role="status">Chargement…</p>
  {:else if formState === "not-found"}
    <p>Cette dépense est introuvable.</p>
  {:else}
    <form onsubmit={handleSubmit} novalidate>
      <div class="field">
        <label for="expense-category">Catégorie</label>
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
        label="Montant"
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
        hint="Facultatif"
        bind:value={description}
        disabled={formState === "submitting"}
      />

      {#if formState === "error"}
        <FormError messages={errorMessages} />
      {/if}

      <Button type="submit" disabled={formState === "submitting"}>
        {formState === "submitting" ? "Enregistrement…" : "Enregistrer les modifications"}
      </Button>
    </form>
  {/if}

  <p><a href="/expenses">Retour aux dépenses</a></p>
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
