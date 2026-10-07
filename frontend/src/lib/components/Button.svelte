<script>
  // Shared button — issue #104. Replaces the near-identical `<button>` +
  // <style> block that login/+page.svelte and register/+page.svelte each
  // defined on their own.
  import "../styles/tokens.css";

  /**
   * @typedef {Object} Props
   * @property {"primary" | "secondary"} [variant]
   * @property {"button" | "submit"} [type]
   * @property {boolean} [disabled]
   * @property {import("svelte").Snippet} children
   */

  /** @type {Props & Record<string, unknown>} */
  let { variant = "primary", type = "button", disabled = false, children, ...rest } =
    $props();
</script>

<button {type} {disabled} class={variant} {...rest}>
  {@render children?.()}
</button>

<style>
  button {
    font-size: var(--font-size-base);
    padding: var(--space-sm) var(--space-lg);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-primary);
    cursor: pointer;
  }

  button:disabled {
    cursor: default;
    opacity: 0.65;
  }

  button.primary {
    background: var(--color-primary);
    color: #fff;
  }

  button.secondary {
    background: transparent;
    color: var(--color-primary);
  }

  button:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 2px;
  }
</style>
