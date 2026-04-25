<script>
  import { onMount } from 'svelte';
  import { settings } from '../../../stores/settings';

  let loading = true;
  let error = '';
  let downloadClients = [];
  let enabledMap = {};
  let activeClient = 'slskd';

  onMount(async () => {
    loading = true;
    try {
      await settings.load();
      const resp = await fetch('/api/providers/download-clients');
      if (resp.ok) {
        downloadClients = await resp.json();
      } else {
        downloadClients = [];
      }

      // Initialize enabled map from settings store data if present
      const current = $settings?.data?.download_clients || {};
      enabledMap = {};
      (downloadClients || []).forEach((c) => {
        const key = c.name || c.id || c.service || '';
        enabledMap[key] = (current[key] === true) || !!c.enabled;
      });
    } catch (err) {
      console.error('Failed to fetch download clients:', err);
      error = err.message || String(err);
    } finally {
      loading = false;
    }
  });

  function clientKey(c) {
    return c?.name || c?.id || c?.service || '';
  }

  // note: keep small helper in-module to avoid polluting markup
  async function toggleClient(key, value) {
    enabledMap = { ...enabledMap, [key]: !!value };
    try {
      await settings.save({ download_clients: { [key]: !!value } });
    } catch (err) {
      console.error('Failed to save download client setting:', err);
    }
  }
</script>

<section>
  <h1>Download Clients</h1>
  <p class="page-description">Configure download clients for obtaining music files</p>
  
  {#if loading}
    <p>Loading download clients...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else}
    {#if downloadClients.length === 0}
      <p>No download clients available.</p>
    {:else}
      <div class="clients-list">
        {#each downloadClients as client (client.name || client.id || client.service)}
          <div class="client-row">
            <label class="form-group">
              <span class="label-text">{client.display_name || client.name || clientKey(client)}</span>
              <input type="checkbox" checked={!!enabledMap[clientKey(client)]} on:change={(e) => toggleClient(clientKey(client), e.target.checked)} />
            </label>
          </div>
        {/each}
      </div>
    {/if}
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