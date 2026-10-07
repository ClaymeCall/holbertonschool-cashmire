<script>
  // Shared form-level error alert — issue #104. Replaces the near-identical
  // `.error[role=alert]` block duplicated across login/+page.svelte (one
  // message) and register/+page.svelte (one message, or a list).
  import "../styles/tokens.css";

  /** @type {{ messages?: string[] }} */
  let { messages = [] } = $props();
</script>

{#if messages.length > 0}
  <div class="error" role="alert">
    {#if messages.length === 1}
      <p>{messages[0]}</p>
    {:else}
      <ul>
        {#each messages as message}
          <li>{message}</li>
        {/each}
      </ul>
    {/if}
  </div>
{/if}

<style>
  .error {
    color: var(--color-error-text);
    background: var(--color-error-bg);
    border-left: 4px solid var(--color-error-border);
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--radius-sm);
    margin-bottom: var(--space-lg);
  }

  .error ul {
    margin: 0;
    padding-left: var(--space-xl);
  }

  .error p {
    margin: 0;
  }
</style>
