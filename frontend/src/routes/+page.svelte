<script>
  import { onMount } from "svelte";

  const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
  let status = "checking...";

  onMount(async () => {
    try {
      const res = await fetch(`${apiUrl}/api/health/`);
      const data = await res.json();
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
