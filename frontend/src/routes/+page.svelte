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
  <p>API status: {status}</p>
</main>
