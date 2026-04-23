<script>
  import { onMount } from 'svelte';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';

  let plugins = [];
  let repos = [];
  let loadError = '';
  let isLoading = true;
  let downloading = null;

  let showReposModal = false;
  let newRepoUrl = '';

  async function loadStore() {
    isLoading = true;
    try {
      const response = await apiClient.get('/system/plugins/store');
      plugins = response.data?.plugins ?? [];
    } catch (err) {
      loadError = 'Failed to load plugin store. Check backend connection.';
      console.error(err);
    } finally {
      isLoading = false;
    }
  }

  async function loadRepos() {
    try {
      const response = await apiClient.get('/system/plugins/repos');
      repos = response.data?.repos ?? [];
    } catch (err) {
      console.error('Failed to load repos:', err);
    }
  }

  onMount(async () => {
    await loadRepos();
    await loadStore();
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

  async function addRepo() {
    if (!newRepoUrl.trim()) return;
    try {
      await apiClient.post('/system/plugins/repos', { url: newRepoUrl.trim() });
      newRepoUrl = '';
      await loadRepos();
      await loadStore();
      feedback.addToast('Repository added', 'success');
    } catch (err) {
      feedback.addToast('Failed to add repository', 'error');
    }
  }

  async function removeRepo(url) {
    try {
      await apiClient.delete('/system/plugins/repos', { data: { url } });
      await loadRepos();
      await loadStore();
      feedback.addToast('Repository removed', 'success');
    } catch (err) {
      feedback.addToast('Failed to remove repository', 'error');
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
    <button class="btn-manage-repos active:scale-95 transition-all duration-200" on:click={() => showReposModal = !showReposModal}>
      {showReposModal ? 'Close Repositories' : 'Manage Repositories'}
    </button>
  </header>

  {#if showReposModal}
    <div class="repos-panel">
      <h2>Configured Repositories</h2>
      <ul class="repo-list">
        {#each repos as repo}
          <li>
            <span class="repo-url">{repo}</span>
            {#if repo !== 'https://github.com/bheem1224/EchoSync/tree/main/plugins'}
              <button class="btn-remove active:scale-95 transition-all duration-200" on:click={() => removeRepo(repo)}>Remove</button>
            {:else}
              <span class="default-badge">Official</span>
            {/if}
          </li>
        {/each}
      </ul>
      <div class="add-repo">
        <input type="text" placeholder="https://github.com/user/repo" bind:value={newRepoUrl} />
        <button on:click={addRepo} disabled={!newRepoUrl.trim()}>Add Repository</button>
      </div>
    </div>
  {/if}

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
              class="btn-install active:scale-95 transition-all duration-200"
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

  .page__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .subtitle {
    color: var(--muted);
    font-size: 14px;
    max-width: 640px;
    margin-top: 4px;
  }

  .btn-manage-repos {
    padding: 8px 16px;
    border-radius: 8px;
    background: var(--surface-2, rgba(255, 255, 255, 0.1));
    border: 1px solid var(--border);
    color: var(--text);
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
  }

  .btn-manage-repos:hover {
    background: var(--surface-3, rgba(255, 255, 255, 0.15));
  }

  .repos-panel {
    background: var(--surface-1, rgba(0, 0, 0, 0.2));
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .repos-panel h2 {
    font-size: 16px;
    margin: 0;
  }

  .repo-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .repo-list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(255, 255, 255, 0.05);
    padding: 10px 14px;
    border-radius: 8px;
  }

  .repo-url {
    font-family: monospace;
    font-size: 13px;
    color: var(--text);
    word-break: break-all;
  }

  .btn-remove {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    border: none;
    padding: 4px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
  }

  .btn-remove:hover {
    background: rgba(239, 68, 68, 0.3);
  }

  .default-badge {
    font-size: 12px;
    color: var(--muted);
    background: rgba(255, 255, 255, 0.1);
    padding: 4px 10px;
    border-radius: 6px;
  }

  .add-repo {
    display: flex;
    gap: 12px;
    margin-top: 8px;
  }

  .add-repo input {
    flex: 1;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 14px;
    color: var(--text);
    font-family: monospace;
    font-size: 13px;
  }

  .add-repo button {
    padding: 8px 16px;
    border-radius: 8px;
    background: var(--accent);
    border: none;
    color: #fff;
    cursor: pointer;
    font-weight: 600;
    font-size: 13px;
  }

  .add-repo button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
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
