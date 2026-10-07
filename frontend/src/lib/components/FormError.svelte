<script>
  // Shared form-level error alert — issue #104. Replaces the near-identical
  // `.error[role=alert]` block duplicated across login/+page.svelte (one
  // message) and register/+page.svelte (one message, or a list).
  import { CircleAlert } from "@lucide/svelte";
  import "../styles/tokens.css";

  /** @type {{ messages?: string[] }} */
  let { messages = [] } = $props();
</script>

{#if messages.length > 0}
  <div class="error" role="alert">
    <CircleAlert size={18} />
    <div class="error-text">
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
  </div>
{/if}

<style>
  .error {
    display: flex;
    align-items: flex-start;
    gap: var(--space-sm);
    color: var(--color-error-text);
    background: var(--color-error-bg);
    border-left: 4px solid var(--color-error-border);
    padding: var(--space-sm) var(--space-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--space-lg);
  }

  .error :global(svg) {
    flex-shrink: 0;
    margin-top: 0.15em;
  }

  .error-text {
    min-width: 0;
  }

  .error ul {
    margin: 0;
    padding-left: var(--space-xl);
  }

  .error p {
    margin: 0;
  }
</style>
