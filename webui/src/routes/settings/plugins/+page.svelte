<script>
  import { onMount } from 'svelte';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';

  let plugins = [];
  let loadError = '';
  let saving = false;
  let showRestartDialog = false;

  // Track the last-saved state so we can detect pending changes
  let savedSnapshot = '';
  $: pendingChanges = savedSnapshot !== JSON.stringify(plugins.map((p) => ({ id: p.id, enabled: p.enabled })));

  onMount(async () => {
    try {
      const response = await apiClient.get('/system/plugins');
      plugins = (response.data?.plugins ?? []).map((p) => ({ ...p }));
      savedSnapshot = JSON.stringify(plugins.map((p) => ({ id: p.id, enabled: p.enabled })));
    } catch (err) {
      loadError = 'Failed to load plugins. Check backend connection.';
      console.error(err);
    }
  });

  function togglePlugin(plugin) {
    plugin.enabled = !plugin.enabled;
    plugins = plugins; // trigger reactivity
  }

  function resetChanges() {
    const saved = JSON.parse(savedSnapshot);
    plugins = plugins.map((p) => {
      const snap = saved.find((s) => s.id === p.id);
      return snap ? { ...p, enabled: snap.enabled } : p;
    });
  }

  async function saveChanges() {
    if (!pendingChanges || saving) return;
    saving = true;
    try {
      const disabledIds = plugins.filter((p) => !p.enabled).map((p) => p.id);
      await apiClient.post('/system/plugins/config', { disabled_providers: disabledIds });
      savedSnapshot = JSON.stringify(plugins.map((p) => ({ id: p.id, enabled: p.enabled })));
      showRestartDialog = true;
    } catch (err) {
      feedback.addToast('Failed to save plugin state.', 'error');
      console.error(err);
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Installed Plugins • SoulSync</title>
</svelte:head>

<!-- Restart-required dialog -->
{#if showRestartDialog}
  <div class="dialog-backdrop" role="presentation" on:click={() => (showRestartDialog = false)}>
    <div
      class="dialog"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      on:click|stopPropagation
      on:keydown={(e) => e.key === 'Escape' && (showRestartDialog = false)}
    >
      <div class="dialog-icon">🔄</div>
      <h2 class="dialog-title">Restart Required</h2>
      <p class="dialog-body">
        Your plugin changes have been saved to <code>config.json</code>. SoulSync must be restarted
        for plugins to be fully loaded or unloaded — running hooks will not change until the
        process restarts.
      </p>
      <button class="dialog-btn" on:click={() => (showRestartDialog = false)}>Got it</button>
    </div>
  </div>
{/if}

<section class="page">
  <header class="page__header">
    <div>
      <h1>Installed Plugins</h1>
      <p class="subtitle">
        System plugins extend or modify SoulSync's behaviour. Unlike Music Providers — which are
        data sources such as Spotify or Slskd — plugins operate on data that has already been
        fetched (e.g. CJK transliteration, custom matching rules).
      </p>
    </div>
  </header>

  <!-- Pending-changes action bar -->
  {#if pendingChanges}
    <div class="pending-bar">
      <span class="pending-label">⚠ Unsaved changes — a restart will be required to apply them.</span>
      <div class="pending-actions">
        <button class="btn-reset" on:click={resetChanges} disabled={saving}>Reset</button>
        <button class="btn-save" on:click={saveChanges} disabled={saving}>
          {saving ? 'Saving…' : 'Save Changes'}
        </button>
      </div>
    </div>
  {/if}

  {#if loadError}
    <p class="error">{loadError}</p>
  {:else if plugins.length === 0}
    <div class="empty-state">
      <span class="empty-icon">🧩</span>
      <p>No plugins installed. Drop a plugin folder into <code>plugins/</code> and restart.</p>
    </div>
  {:else}
    <div class="plugin-grid">
      {#each plugins as plugin (plugin.id)}
        <div class="plugin-card" class:disabled={!plugin.enabled}>
          <div class="plugin-header">
            <span class="plugin-icon">🧩</span>
            <div>
              <h3 class="plugin-name">{plugin.display_name ?? plugin.id}</h3>
              <span class="plugin-id">{plugin.id}</span>
            </div>
            <label class="toggle" title={plugin.enabled ? 'Disable plugin' : 'Enable plugin'}>
              <input
                type="checkbox"
                checked={plugin.enabled}
                disabled={saving}
                on:change={() => togglePlugin(plugin)}
              />
              <span class="slider"></span>
            </label>
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
            {#if plugin.hooks?.length}
              <span class="meta-chip" title={plugin.hooks.join(', ')}>
                {plugin.hooks.length} hook{plugin.hooks.length === 1 ? '' : 's'}
              </span>
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

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 48px 24px;
    color: var(--muted);
    text-align: center;
  }

  .empty-icon {
    font-size: 40px;
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
    transition: opacity 0.2s;
  }

  .plugin-card.disabled {
    opacity: 0.5;
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

  /* push toggle to the far right */
  .toggle {
    margin-left: auto;
    flex-shrink: 0;
    position: relative;
    display: inline-block;
    width: 40px;
    height: 22px;
    cursor: pointer;
  }

  .toggle input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .slider {
    position: absolute;
    inset: 0;
    background: var(--border);
    border-radius: 22px;
    transition: background 0.2s;
  }

  .slider::before {
    content: '';
    position: absolute;
    width: 16px;
    height: 16px;
    left: 3px;
    top: 3px;
    background: #fff;
    border-radius: 50%;
    transition: transform 0.2s;
  }

  .toggle input:checked + .slider {
    background: var(--accent);
  }

  .toggle input:checked + .slider::before {
    transform: translateX(18px);
  }

  .plugin-description {
    font-size: 13px;
    color: var(--muted);
    margin: 0;
  }

  .plugin-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .meta-chip {
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--border);
    color: var(--muted);
  }

  .error {
    color: var(--error);
  }

  /* ── Pending-changes bar ── */
  .pending-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 10px;
    background: rgba(251, 191, 36, 0.08);
    border: 1px solid rgba(251, 191, 36, 0.35);
  }

  .pending-label {
    font-size: 13px;
    color: #fbbf24;
  }

  .pending-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }

  .btn-reset {
    padding: 6px 14px;
    border-radius: 7px;
    font-size: 13px;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    cursor: pointer;
  }

  .btn-reset:hover:not(:disabled) {
    background: rgba(255,255,255,0.05);
  }

  .btn-save {
    padding: 6px 16px;
    border-radius: 7px;
    font-size: 13px;
    font-weight: 600;
    background: var(--accent);
    border: none;
    color: #fff;
    cursor: pointer;
  }

  .btn-save:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  .btn-save:disabled,
  .btn-reset:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* ── Restart dialog ── */
  .dialog-backdrop {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: rgba(0, 0, 0, 0.65);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .dialog {
    background: var(--surface, #1e2330);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px 28px;
    max-width: 440px;
    width: 90%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    text-align: center;
  }

  .dialog-icon {
    font-size: 40px;
  }

  .dialog-title {
    font-size: 18px;
    font-weight: 700;
    margin: 0;
  }

  .dialog-body {
    font-size: 14px;
    color: var(--muted);
    line-height: 1.6;
    margin: 0;
  }

  .dialog-body code {
    font-family: monospace;
    font-size: 12px;
    background: rgba(255,255,255,0.07);
    padding: 1px 5px;
    border-radius: 4px;
  }

  .dialog-btn {
    margin-top: 8px;
    padding: 8px 28px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    background: var(--accent);
    border: none;
    color: #fff;
    cursor: pointer;
  }

  .dialog-btn:hover {
    filter: brightness(1.1);
  }
</style>
