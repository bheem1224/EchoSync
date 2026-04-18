<script>
  import { onMount } from 'svelte';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';

  let plugins = [];
  let loadError = '';
  let isLoading = true;
  let downloading = null;

  onMount(async () => {
    try {
      const response = await apiClient.get('/system/plugins/store');
      plugins = response.data?.plugins ?? [];
    } catch (err) {
      loadError = 'Failed to load plugin store. Check backend connection.';
      console.error(err);
    } finally {
      isLoading = false;
    }
  });

  async function installPlugin(plugin) {
    if (downloading) return;
    downloading = plugin.id || plugin.name;

    try {
      await apiClient.post('/system/plugins/install', { plugin });
      feedback.addToast(`Successfully installed ${plugin.name}. Restart required.`, 'success');
      // Mark as installed locally so UI updates
      plugins = plugins.map(p =>
        (p.id === plugin.id || p.name === plugin.name) ? { ...p, _installed: true } : p
      );
    } catch (err) {
      feedback.addToast(`Failed to install ${plugin.name}.`, 'error');
      console.error(err);
    } finally {
      downloading = null;
    }
  }
</script>

<svelte:head>
  <title>Plugin Store • Echosync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div>
      <h1>Plugin Store</h1>
      <p class="subtitle">
        Browse and install community and official plugins to extend Echosync's functionality.
      </p>
    </div>
  </header>

  {#if isLoading}
    <div class="loading-state">
      <span class="loading-icon">⏳</span>
      <p>Loading plugin store...</p>
    </div>
  {:else if loadError}
    <p class="error">{loadError}</p>
  {:else if plugins.length === 0}
    <div class="empty-state">
      <span class="empty-icon">🏪</span>
      <p>No plugins found in the store repositories.</p>
    </div>
  {:else}
    <div class="plugin-grid">
      {#each plugins as plugin (plugin.id || plugin.name)}
        <div class="plugin-card">
          <div class="plugin-header">
            <span class="plugin-icon">📦</span>
            <div>
              <h3 class="plugin-name">{plugin.name}</h3>
              <span class="plugin-id">{plugin.id || 'unknown'}</span>
            </div>

            <button
              class="btn-install"
              class:installed={plugin._installed}
              disabled={downloading !== null || plugin._installed}
              on:click={() => installPlugin(plugin)}
            >
              {#if plugin._installed}
                Installed
              {:else if downloading === (plugin.id || plugin.name)}
                Installing...
              {:else}
                Install
              {/if}
            </button>
          </div>

          {#if plugin.description}
            <p class="plugin-description">{plugin.description}</p>
          {/if}

          <div class="plugin-meta">
            {#if plugin.version}
              <span class="meta-chip">v{plugin.version}</span>
            {/if}
            {#if plugin.author}
              <span class="meta-chip">by {plugin.author}</span>
            {/if}
            {#if plugin.type}
              <span class="meta-chip type-chip">{plugin.type}</span>
            {/if}
            {#if plugin.verified_source === 'official'}
              <span class="meta-chip official-chip" title="Verified Official Source">✓ Official</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .subtitle {
    color: var(--muted);
    font-size: 14px;
    max-width: 640px;
    margin-top: 4px;
  }

  .empty-state, .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 48px 24px;
    color: var(--muted);
    text-align: center;
  }

  .empty-icon, .loading-icon {
    font-size: 40px;
  }

  .loading-icon {
    animation: spin 2s linear infinite;
  }

  @keyframes spin {
    100% { transform: rotate(360deg); }
  }

  .plugin-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
  }

  .plugin-card {
    background: var(--glass);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .plugin-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
  }

  .plugin-icon {
    font-size: 24px;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .plugin-name {
    font-size: 15px;
    font-weight: 600;
    margin: 0;
  }

  .plugin-id {
    font-size: 11px;
    color: var(--muted);
    font-family: monospace;
  }

  .btn-install {
    margin-left: auto;
    padding: 6px 14px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 600;
    background: var(--accent);
    border: none;
    color: #fff;
    cursor: pointer;
    flex-shrink: 0;
  }

  .btn-install:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  .btn-install:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-install.installed {
    background: rgba(255, 255, 255, 0.1);
    color: var(--muted);
  }

  .plugin-description {
    font-size: 13px;
    color: var(--muted);
    margin: 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .plugin-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: auto;
  }

  .meta-chip {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--border);
    color: var(--muted);
  }

  .type-chip {
    background: rgba(14, 165, 233, 0.1);
    border-color: rgba(14, 165, 233, 0.3);
    color: #38bdf8;
  }

  .official-chip {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
    color: #34d399;
  }

  .error {
    color: var(--error);
  }
</style>
