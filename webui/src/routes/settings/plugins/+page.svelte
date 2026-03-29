<script>
  import { onMount } from 'svelte';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';

  let plugins = [];
  let loadError = '';
  let saving = false;

  onMount(async () => {
    try {
      const response = await apiClient.get('/system/plugins');
      plugins = (response.data?.plugins ?? []).map((p) => ({ ...p }));
    } catch (err) {
      loadError = 'Failed to load plugins. Check backend connection.';
      console.error(err);
    }
  });

  async function togglePlugin(plugin) {
    plugin.enabled = !plugin.enabled;
    plugins = plugins; // trigger reactivity
    try {
      saving = true;
      const disabledIds = plugins.filter((p) => !p.enabled).map((p) => p.id);
      await apiClient.post('/system/plugins/config', { disabled_providers: disabledIds });
      feedback.addToast(
        `Plugin "${plugin.display_name}" ${plugin.enabled ? 'enabled' : 'disabled'}.`,
        'success'
      );
    } catch (err) {
      feedback.addToast('Failed to save plugin state.', 'error');
      // Roll back optimistic toggle
      plugin.enabled = !plugin.enabled;
      plugins = plugins;
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Installed Plugins • SoulSync</title>
</svelte:head>

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
              <span class="slider" />
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
</style>
