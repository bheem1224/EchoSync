<script>
  import { onMount } from 'svelte';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';
  import ConfirmDialog from '../../../components/ConfirmDialog.svelte';

  let plugins = [];
  let repos = [];
  let loadError = '';
  let isLoading = true;
  let downloading = null;

  let showReposModal = false;
  let newRepoUrl = '';
  let showOverflowMenu = false;
  let betaOpt = false;
  let devMode = false;
  let showBetaWarning = false;

  async function handleBetaToggle() {
    if (!betaOpt) {
      showBetaWarning = true;
    } else {
      await proceedWithBetaToggle();
    }
  }

  async function proceedWithBetaToggle() {
    showBetaWarning = false;
    showOverflowMenu = false;
    await setUiBetaOpt(!betaOpt);
    setTimeout(() => window.location.reload(), 500);
  }

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
    await loadUiBeta();
    await loadStore();
  });

  async function loadUiBeta() {
    try {
      const resp = await apiClient.get('/manager/ui-beta');
      if (resp && resp.data) {
        betaOpt = !!resp.data.beta_opt_in;
        devMode = !!resp.data.dev_mode;
      }
    } catch (err) {
      console.debug('Failed to load ui-beta opt state:', err);
    }
  }

  async function setUiBetaOpt(val) {
    try {
      const resp = await apiClient.post('/manager/ui-beta', { beta_opt_in: !!val });
      if (resp && resp.data) {
        betaOpt = !!resp.data.beta_opt_in;
        feedback.addToast(`Beta UI opt ${betaOpt ? 'enabled' : 'disabled'}`, 'success');
      }
    } catch (err) {
      feedback.addToast('Failed to update beta opt state', 'error');
      console.error('Failed to set ui-beta:', err);
    }
  }

  async function installPlugin(plugin, isUpdate = false) {
    if (downloading) return;
    downloading = plugin.id || plugin.name;

    try {
      await apiClient.post('/system/plugins/install', { plugin });
      feedback.addToast(`Successfully ${isUpdate ? 'updated' : 'installed'} ${plugin.name}. Restart required.`, 'success');
      // Mark as installed locally so UI updates
      plugins = plugins.map(p =>
        (p.id === plugin.id || p.name === plugin.name) ? { ...p, _installed: true, is_installed: true, update_available: false, installed_version: p.version } : p
      );
    } catch (err) {
      feedback.addToast(`Failed to ${isUpdate ? 'update' : 'install'} ${plugin.name}.`, 'error');
      console.error(err);
    } finally {
      downloading = null;
    }
  }

  let openMenuId = null;
  let showUninstallConfirm = false;
  let pluginToUninstall = null;
  let uninstalling = false;

  function requestUninstall(plugin) {
    pluginToUninstall = plugin;
    showUninstallConfirm = true;
    openMenuId = null;
  }

  async function executeUninstall() {
    if (!pluginToUninstall || uninstalling) return;
    uninstalling = true;
    try {
      await apiClient.post('/system/plugins/uninstall', { id: pluginToUninstall.id || pluginToUninstall.name });
      feedback.addToast(`Successfully uninstalled ${pluginToUninstall.name}. Restart required.`, 'success');
      plugins = plugins.map(p =>
        (p.id === pluginToUninstall.id || p.name === pluginToUninstall.name) ? { ...p, _installed: false, is_installed: false, update_available: false } : p
      );
    } catch (err) {
      feedback.addToast(`Failed to uninstall ${pluginToUninstall.name}.`, 'error');
      console.error(err);
    } finally {
      uninstalling = false;
      showUninstallConfirm = false;
      pluginToUninstall = null;
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
    <div class="header-actions">
      <button class="btn-manage-repos active:scale-95 transition-all duration-200" on:click={() => showReposModal = !showReposModal}>
        {showReposModal ? 'Close Repositories' : 'Manage Repositories'}
      </button>

      <div class="overflow-menu relative inline-block">
        <button class="btn-ellipsis p-2 rounded-global" aria-haspopup="true" aria-expanded={showOverflowMenu} on:click={() => showOverflowMenu = !showOverflowMenu} title="More">
          ⋯
        </button>

        {#if showOverflowMenu}
          <div class="menu absolute right-0 mt-2 w-56 bg-surface border border-glass-border rounded-global shadow-lg z-40">
            <button class="menu-item" on:click={() => { showReposModal = true; showOverflowMenu = false; }}>Manage Repositories</button>
            <div class="menu-divider"></div>
            <button class="menu-item" on:click={handleBetaToggle}>
              {betaOpt ? 'Opt-out Beta Plugins' : 'Opt-in Beta Plugins'} {#if devMode}<span class="badge">dev</span>{/if}
            </button>
          </div>
        {/if}
      </div>
    </div>
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
          <div class="plugin-header relative pr-6">
            <span class="plugin-icon">📦</span>
            <div>
              <h3 class="plugin-name">{plugin.name}</h3>
              <span class="plugin-id">{plugin.id || 'unknown'}</span>
            </div>

            {#if plugin._installed || plugin.is_installed}
              <div class="kebab-menu absolute top-0 right-0">
                <button class="text-white opacity-50 hover:opacity-100 p-1 px-2 rounded-global bg-transparent border-none cursor-pointer" on:click={() => openMenuId = (openMenuId === (plugin.id || plugin.name) ? null : (plugin.id || plugin.name))}>⋮</button>
                {#if openMenuId === (plugin.id || plugin.name)}
                  <div class="absolute right-0 top-8 w-32 bg-surface border border-glass-border shadow-lg rounded-global z-50 overflow-hidden">
                    <button class="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-black/20 border-none bg-transparent cursor-pointer" on:click={() => requestUninstall(plugin)}>Uninstall</button>
                  </div>
                {/if}
              </div>
            {/if}
          </div>

          {#if plugin.description}
            <p class="plugin-description">{plugin.description}</p>
          {/if}

          <div class="plugin-meta flex items-center justify-between mt-auto">
            <div class="flex flex-wrap gap-1.5">
              {#if plugin.version}
                <span class="meta-chip">
                  {#if (plugin._installed || plugin.is_installed) && plugin.update_available && plugin.installed_version}
                    v{plugin.installed_version} ➔ v{plugin.version}
                  {:else}
                    v{plugin.version}
                  {/if}
                </span>
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

            <div class="action-zone flex-shrink-0 ml-2">
              {#if plugin.update_available}
                <button
                  class="bg-green-600 hover:bg-green-500 text-white px-3 py-1.5 rounded-global text-xs font-bold border-none cursor-pointer active:scale-95 transition-all whitespace-nowrap"
                  disabled={downloading !== null}
                  on:click={() => installPlugin(plugin, true)}
                >
                  {downloading === (plugin.id || plugin.name) ? 'Updating...' : 'Update'}
                </button>
              {:else if plugin._installed || plugin.is_installed}
                <span class="inline-block bg-black/20 text-slate-400 border border-glass-border px-3 py-1.5 rounded-global text-xs font-bold whitespace-nowrap select-none">
                  Installed ✓
                </span>
              {:else}
                <button
                  class="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-global text-xs font-bold border-none cursor-pointer active:scale-95 transition-all whitespace-nowrap"
                  disabled={downloading !== null}
                  on:click={() => installPlugin(plugin)}
                >
                  {downloading === (plugin.id || plugin.name) ? 'Installing...' : 'Install'}
                </button>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>

{#if showBetaWarning}
  <ConfirmDialog 
      title="⚠️ Warning: Beta Plugins"
      confirmText="OK"
      cancelText="Cancel"
      danger={true}
      on:confirm={proceedWithBetaToggle}
      on:cancel={() => showBetaWarning = false}
  >
      <div class="text-sm mt-2">
          Warning: You are opting into Beta Plugin builds. There is a 95% chance of this being broken and completely ruining your UI. Would not recommend. I am not a very good coder. Continue anyway?
      </div>
  </ConfirmDialog>
{/if}

{#if showUninstallConfirm}
  <ConfirmDialog 
      title="🗑️ Uninstall Plugin"
      confirmText={uninstalling ? 'Uninstalling...' : 'Uninstall'}
      cancelText="Cancel"
      danger={true}
      on:confirm={executeUninstall}
      on:cancel={() => showUninstallConfirm = false}
  >
      <div class="text-sm mt-2">
          Are you sure you want to uninstall <strong>{pluginToUninstall?.name}</strong>? This will remove its files and may disable any functionality that relies on it.
          <br/><br/>
          <span class="text-red-400 font-bold">A restart of EchoSync will be required to complete the removal.</span>
      </div>
  </ConfirmDialog>
{/if}

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

  .header-actions { display:flex; gap:8px; align-items:flex-start; }
  .btn-ellipsis { background: transparent; border: 1px solid transparent; color: var(--text); cursor: pointer; font-size: 20px; }
  .menu { padding: 6px; }
  .menu-item { display:block; width:100%; text-align:left; padding:8px 10px; background:transparent; border:none; color:var(--text); cursor:pointer; }
  .menu-item:hover { background: rgba(255,255,255,0.03); }
  .menu-divider { height:1px; background: rgba(255,255,255,0.03); margin:4px 0; }
  .badge { margin-left:8px; padding:2px 6px; border-radius:6px; background:var(--accent); color:#000; font-size:12px; }

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

  .plugin-description {
    font-size: 13px;
    color: var(--muted);
    margin: 0 0 12px 0;
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
