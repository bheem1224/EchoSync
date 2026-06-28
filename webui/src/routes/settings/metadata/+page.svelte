<script>
  import { onMount } from 'svelte';
  import { plugins } from '../../../stores/plugins';
  import { feedback } from '../../../stores/feedback';
  import { getConfig, setConfig } from '../../../stores/config';
  import DynamicPluginLoader from '../../../components/DynamicPluginLoader.svelte';

  // Tabs
  let activeTab = $state('plugins'); // plugins, settings

  // Plugins Logic
  let metadataPlugins = $state([]);
  let loadError = $state('');

  onMount(async () => {
    // Initial Load
    await loadProviders();
    await loadSettings();
  });

  // --- Plugins ---
  async function loadProviders() {
    try {
      await plugins.load().catch(() => {});
      const allProviders = Object.values($plugins?.items ?? []);
      metadataPlugins = allProviders
        .filter(p => !p.disabled)
        .filter(p => {
          return (
            p.capabilities?.fetch_metadata ||
            p.capabilities?.resolve_fingerprint ||
            p.capabilities?.supports_lyrics ||
            p.service_type === 'metadata'
          );
        });
    } catch (err) {
      loadError = 'Failed to load metadata plugins. Check backend connection.';
      console.error(err);
    }
  }

  // --- Settings ---
  async function loadSettings() {
      // Logic preserved for fallback
  }

  function getProviderIcon(pluginName) {
    const icons = { acoustid: '🔍', musicbrainz: '🎵', lrclib: '📝', listenbrainz: '🧠' };
    return icons[pluginName] || '⚙️';
  }
</script>

<svelte:head>
  <title>Metadata Manager • EchoSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div class="page__eyebrow">Intelligence</div>
    <h1>Metadata Manager</h1>
    <p class="subtitle">Manage metadata plugins and enhancement settings.</p>
  </header>

  <div class="tabs">
      <button class="tab-btn" class:active={activeTab === 'plugins'} on:click={() => activeTab = 'plugins'}>Plugins</button>
      <button class="tab-btn" class:active={activeTab === 'settings'} on:click={() => activeTab = 'settings'}>Settings</button>
  </div>

  <div class="tab-content">
      {#if activeTab === 'plugins'}
          {#if loadError}
            <div class="error-card"><p>{loadError}</p></div>
          {:else}
            <!-- 
              Primary: DynamicPluginLoader renders Web Components for active plugins.
              Category "settings_panel" is used for metadata configuration cards.
            -->
            <DynamicPluginLoader category="metadata">
              <svelte:fragment slot="loading">
                <div class="services-loading">
                  <div class="loading-shimmer"></div>
                  <div class="loading-shimmer loading-shimmer--narrow"></div>
                </div>
              </svelte:fragment>

              <svelte:fragment slot="empty-state">
                {#if metadataPlugins.length > 0}
                  <div class="plugins-grid">
                    {#each metadataPlugins as plugin (plugin.id)}
                      <div class="plugin-card">
                        <div class="plugin-header">
                          <div class="plugin-title">
                            <span class="plugin-icon">{getProviderIcon(String(plugin.name || plugin.id).toLowerCase())}</span>
                            <div>
                              <h2>{plugin.display_name || plugin.name}</h2>
                              <p class="plugin-type">
                                {#if plugin.capabilities?.resolve_fingerprint}<span class="badge">Fingerprinting</span>{/if}
                                {#if plugin.capabilities?.fetch_metadata}<span class="badge">Metadata</span>{/if}
                              </p>
                            </div>
                          </div>
                          <div class="plugin-status">
                            {#if plugin.is_configured}
                              <span class="status-badge configured">✓ Configured</span>
                            {:else}
                              <span class="status-badge not-configured">⚠ Not Configured</span>
                            {/if}
                          </div>
                        </div>
                        <p class="plugin-description">{plugin.description ?? 'Metadata plugin service.'}</p>
                        <div class="plugin-actions">
                           <a href="/settings/metadata/{String(plugin.name || plugin.id).toLowerCase()}" class="link">Configure →</a>
                        </div>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <div class="empty-state">
                    <p class="muted">No metadata plugins detected or enabled.</p>
                  </div>
                {/if}
              </svelte:fragment>
            </DynamicPluginLoader>
          {/if}

      {:else if activeTab === 'settings'}
          <div class="settings-card">
              <p class="text-sm text-slate-400">Settings are now automatically managed by the backend auto_importer engine.</p>
          </div>
      {/if}
  </div>
</section>

<style>
  .page { display: flex; flex-direction: column; gap: 24px; max-width: 1000px; }
  
  .page__eyebrow {
    font-size: 10px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.25em;
    color: var(--color-primary);
    margin-bottom: 4px;
  }

  .page__header h1 { margin: 0 0 6px 0; font-size: 28px; font-weight: 700; color: #fff; }
  .subtitle { color: var(--text-muted, rgba(255,255,255,0.45)); font-size: 14px; margin: 0; }

  /* Tabs */
  .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.08)); margin-bottom: 24px; }
  .tab-btn {
      background: none; border: none; padding: 12px 24px; color: var(--text-muted, rgba(255,255,255,0.4)); cursor: pointer; font-weight: 600;
      border-bottom: 2px solid transparent; font-size: 14px; transition: all 0.2s;
  }
  .tab-btn:hover { color: rgba(255,255,255,0.7); }
  .tab-btn.active { color: var(--color-primary, #1db954); border-bottom-color: var(--color-primary, #1db954); }

  /* Plugins Grid */
  .plugins-grid { display: flex; flex-direction: column; gap: 16px; }
  .plugin-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .plugin-header { display: flex; justify-content: space-between; align-items: flex-start; }
  .plugin-title { display: flex; gap: 14px; }
  .plugin-icon { font-size: 32px; background: rgba(255,255,255,0.04); padding: 8px; border-radius: 10px; }
  .plugin-title h2 { margin: 0 0 4px 0; font-size: 18px; font-weight: 700; }
  .plugin-type { display: flex; gap: 6px; }
  .badge { background: rgba(59, 130, 246, 0.1); color: #3b82f6; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
  .status-badge { padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; }
  .status-badge.configured { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
  .status-badge.not-configured { background: rgba(251, 191, 36, 0.1); color: #fbbf24; }
  .plugin-description { color: var(--text-muted, rgba(255,255,255,0.45)); font-size: 13px; line-height: 1.5; margin: 0; }
  
  .link { color: var(--color-primary, #1db954); text-decoration: none; font-weight: 700; font-size: 13px; }
  .link:hover { text-decoration: underline; }

  /* Settings Styles */
  .settings-card { background: rgba(255,255,255,0.03); padding: 24px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.07); max-width: 600px; }

  .services-loading { display: flex; flex-direction: column; gap: 12px; }
  .loading-shimmer {
    height: 100px; border-radius: 14px;
    background: linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 100%);
    background-size: 200% 100%; animation: shimmer 1.4s ease-in-out infinite;
  }
  @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

  .empty-state { text-align: center; color: var(--text-muted, rgba(255,255,255,0.4)); padding: 60px; border: 1px dashed rgba(255,255,255,0.08); border-radius: 16px; }
</style>
