<script>
  import { onMount } from 'svelte';

  let loading = true;
  let error = '';
  let hasSlskd = false;

  onMount(async () => {
    try {
      const response = await fetch('/api/providers/download-clients');
      if (!response.ok) {
        throw new Error(`Failed to fetch download clients: ${response.statusText}`);
      }
      const downloadClients = await response.json();
      hasSlskd = downloadClients.some(c => c.name === 'slskd' || c.name === 'soulseek');
      loading = false;
    } catch (err) {
      console.error('Failed to fetch download clients:', err);
      error = err.message;
      loading = false;
    }
  });
</script>

<section>
  <h1>Download Clients</h1>
  <p class="page-description">Configure download clients for obtaining music files</p>
  
  {#if loading}
    <p>Loading download clients...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else}
    <p>No download clients available.</p>
  {/if}
</section>

<style>
  h1 {
    margin-bottom: 8px;
    font-size: 28px;
    font-weight: 600;
    color: var(--text-main, #ffffff);
  }

  .page-description {
    color: var(--text-muted, #8b9bb4);
    margin-bottom: 24px;
    font-size: 14px;
  }
  
  .error {
    color: var(--color-error, #ff5252);
    padding: 12px;
    background: rgba(255, 82, 82, 0.1);
    border-radius: 6px;
    border-left: 3px solid #ff5252;
  }
</style>