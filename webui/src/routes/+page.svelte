<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  onMount(() => {
    goto('/dashboard');
  });
</script>

<svelte:head>
  <title>Echosync</title>
</svelte:head>

<div class="redirect">
  <p>Redirecting to Dashboard...</p>
</div>

<style>
  .redirect {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    color: #e2e8f0;
    background: #0f172a;
  }
</style>