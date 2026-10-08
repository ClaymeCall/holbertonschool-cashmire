<script>
  // Shared labelled text input — issue #104. Replaces the near-identical
  // `.field` (label + input + optional hint) markup duplicated across
  // login/+page.svelte and register/+page.svelte.
  import "../styles/tokens.css";

  /**
   * @typedef {Object} Props
   * @property {string} id
   * @property {string} label
   * @property {string} [type]
   * @property {string} value
   * @property {string} [hint]
   * @property {boolean} [disabled]
   * @property {boolean} [required]
   */

  /** @type {Props & Record<string, unknown>} */
  let {
    id,
    label,
    type = "text",
    value = $bindable(""),
    hint,
    disabled = false,
    required = false,
    ...rest
  } = $props();
</script>

<div class="field">
  <label for={id}>{label}</label>
  <input {id} {type} {disabled} {required} bind:value {...rest} />
  {#if hint}
    <p class="hint">{hint}</p>
  {/if}
</div>

<style>
  .field {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    margin-bottom: var(--space-lg);
  }

  label {
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    font-weight: 500;
    letter-spacing: var(--tracking-mono-label);
    text-transform: uppercase;
    color: var(--color-heading);
  }

  input {
    font-family: var(--font-body);
    font-size: var(--font-size-base);
    padding: var(--space-sm) 0.75rem;
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    transition: border-color var(--motion-duration) var(--motion-ease);
  }

  input:hover {
    border-color: var(--color-camel-deep);
  }

  input:focus-visible {
    outline: var(--focus-ring-width) solid var(--focus-ring-color);
    outline-offset: 1px;
  }

  .hint {
    margin: 0;
    font-size: 0.85em;
    color: var(--color-text-muted);
  }
</style>
