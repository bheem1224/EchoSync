<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import { feedback } from '../../../stores/feedback';
  import { getConfig, setConfig } from '../../../stores/config';
  import DynamicPluginLoader from '../../../components/DynamicPluginLoader.svelte';

  // Tabs
  let activeTab = 'providers'; // providers, settings

  // Providers Logic
  let metadataProviders = [];
  let loadError = '';

  onMount(async () => {
    // Initial Load
    await loadProviders();
    await loadSettings();
  });

  // --- Providers ---
  async function loadProviders() {
    try {
      await providers.load().catch(() => {});
      const allProviders = Object.values($providers?.items ?? []);
      metadataProviders = allProviders
        .filter(p => !p.disabled)
        .filter(p => {
          return (
            p.capabilities?.fetch_metadata ||
            p.capabilities?.resolve_fingerprint ||
            p.service_type === 'metadata' ||
            ['musicbrainz', 'acoustid', 'lrclib', 'listenbrainz'].includes((p.id || p.name || '').toLowerCase().replace('core.', ''))
          );
        });
    } catch (err) {
      loadError = 'Failed to load metadata providers. Check backend connection.';
      console.error(err);
    }
  }

  // --- Settings ---
  async function loadSettings() {
      // Logic preserved for fallback
  }

  function getProviderIcon(providerName) {
    const icons = { acoustid: '🔍', musicbrainz: '🎵', lrclib: '📝', listenbrainz: '🧠' };
    return icons[providerName] || '⚙️';
  }
</script>

<svelte:head>
  <title>Metadata Manager • EchoSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div class="page__eyebrow">Intelligence</div>
    <h1>Metadata Manager</h1>
    <p class="subtitle">Manage metadata providers and enhancement settings.</p>
  </header>

  <div class="tabs">
      <button class="tab-btn" class:active={activeTab === 'providers'} on:click={() => activeTab = 'providers'}>Providers</button>
      <button class="tab-btn" class:active={activeTab === 'settings'} on:click={() => activeTab = 'settings'}>Settings</button>
  </div>

  <div class="tab-content">
      {#if activeTab === 'providers'}
          {#if loadError}
            <div class="error-card"><p>{loadError}</p></div>
          {:else}
            <!-- 
              Primary: DynamicPluginLoader renders Web Components for active plugins.
              Category "settings_panel" is used for metadata configuration cards.
            -->
            <DynamicPluginLoader category="settings_panel">
              <svelte:fragment slot="loading">
                <div class="services-loading">
                  <div class="loading-shimmer"></div>
                  <div class="loading-shimmer loading-shimmer--narrow"></div>
                </div>
              </svelte:fragment>

              <svelte:fragment slot="empty-state">
                {#if metadataProviders.length > 0}
                  <div class="providers-grid">
                    {#each metadataProviders as provider (provider.id)}
                      <div class="provider-card">
                        <div class="provider-header">
                          <div class="provider-title">
                            <span class="provider-icon">{getProviderIcon(provider.id.replace('core.', ''))}</span>
                            <div>
                              <h2>{provider.display_name || provider.name}</h2>
                              <p class="provider-type">
                                {#if provider.capabilities?.resolve_fingerprint}<span class="badge">Fingerprinting</span>{/if}
                                {#if provider.capabilities?.fetch_metadata}<span class="badge">Metadata</span>{/if}
                              </p>
                            </div>
                          </div>
                          <div class="provider-status">
                            {#if provider.is_configured}
                              <span class="status-badge configured">✓ Configured</span>
                            {:else}
                              <span class="status-badge not-configured">⚠ Not Configured</span>
                            {/if}
                          </div>
                        </div>
                        <p class="provider-description">{provider.description ?? 'Metadata provider service.'}</p>
                        <div class="provider-actions">
                           <a href="/settings/metadata/{provider.id.replace('core.', '')}" class="link">Configure →</a>
                        </div>
                      </div>
                    {/each}
                  </div>
                {:else}
                  <div class="empty-state">
                    <p class="muted">No metadata providers detected or enabled.</p>
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

  /* Providers Grid */
  .providers-grid { display: flex; flex-direction: column; gap: 16px; }
  .provider-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .provider-header { display: flex; justify-content: space-between; align-items: flex-start; }
  .provider-title { display: flex; gap: 14px; }
  .provider-icon { font-size: 32px; background: rgba(255,255,255,0.04); padding: 8px; border-radius: 10px; }
  .provider-title h2 { margin: 0 0 4px 0; font-size: 18px; font-weight: 700; }
  .provider-type { display: flex; gap: 6px; }
  .badge { background: rgba(59, 130, 246, 0.1); color: #3b82f6; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
  .status-badge { padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; }
  .status-badge.configured { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
  .status-badge.not-configured { background: rgba(251, 191, 36, 0.1); color: #fbbf24; }
  .provider-description { color: var(--text-muted, rgba(255,255,255,0.45)); font-size: 13px; line-height: 1.5; margin: 0; }
  
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
