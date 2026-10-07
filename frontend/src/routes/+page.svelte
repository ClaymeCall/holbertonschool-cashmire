<script>
  import { onMount } from "svelte";
  import { apiFetch } from "$lib/api";

  let status = "checking...";

  onMount(async () => {
    try {
      const data = await apiFetch("/api/health/");
      status = data.status;
    } catch (err) {
      status = "unreachable";
    }
  });
</script>

<main>
  <h1>Cashmire</h1>
  <p>API status: <code>{status}</code></p>
</main>

<style>
  main {
    max-width: 60ch;
    margin: 0 auto;
    padding: var(--space-3xl) var(--space-xl);
  }

  h1 {
    font-size: 2.25rem;
    font-style: italic;
    font-weight: 300;
  }
</style>
