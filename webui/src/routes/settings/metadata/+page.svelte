<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import { feedback } from '../../../stores/feedback';
  import { getConfig, setConfig } from '../../../stores/config';

  // Tabs
  let activeTab = 'providers'; // providers, settings

  // Providers Logic
  let metadataProviders = [];
  let loadError = '';
  let providerConfigs = {};
  let savingProvider = '';
  let visibleFields = {};

  // Settings Logic
  let confidenceThreshold = 90;
  let overwriteTags = true;
  let embedCoverArt = true;
  let settingsLoaded = false;

  onMount(async () => {
    // Initial Load
    await loadProviders();
    await loadSettings();
  });

  // --- Providers ---
  async function loadProviders() {
    try {
      await providers.load();
      const allProviders = Object.values($providers?.items ?? []);
      metadataProviders = allProviders.filter(p => {
        return p.capabilities?.fetch_metadata ||
               p.capabilities?.resolve_fingerprint ||
               p.service_type === 'metadata';
      });

      for (const provider of metadataProviders) {
        await loadProviderConfig(provider.name);
      }
    } catch (err) {
      loadError = 'Failed to load metadata providers. Check backend connection.';
      console.error(err);
    }
  }

  async function loadProviderConfig(providerName) {
    try {
      if (!providerConfigs[providerName]) providerConfigs[providerName] = {};
      const response = await fetch(`/api/providers/${providerName}/credentials`);
      if (response.ok) {
        const data = await response.json();
        providerConfigs[providerName] = data.credentials || {};
      }
    } catch (err) {
      console.error(`Failed to load config for ${providerName}:`, err);
    }
  }

  async function saveProviderCredentials(providerName, credentials) {
    try {
      savingProvider = providerName;
      feedback.setLoading(true);
      const response = await fetch(`/api/providers/${providerName}/credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credentials })
      });
      if (response.ok) {
        feedback.addToast(`${providerName} credentials saved`, 'success');
        await loadProviders(); // reload providers so is_configured badge updates
      } else {
        const error = await response.json();
        feedback.addToast(`Failed to save: ${error.error || 'Unknown error'}`, 'error');
      }
    } catch (err) {
      feedback.addToast(`Error saving ${providerName} credentials`, 'error');
    } finally {
      savingProvider = '';
      feedback.setLoading(false);
    }
  }

  function getProviderIcon(providerName) {
    const icons = { acoustid: '🔍', musicbrainz: '🎵' };
    return icons[providerName] || '⚙️';
  }

  function getProviderDescription(provider) {
    const descriptions = {
      acoustid: 'Audio fingerprinting service that identifies music files by their acoustic signature',
      musicbrainz: 'Open music encyclopedia providing comprehensive metadata for recordings, releases, and artists'
    };
    return descriptions[provider.name] || provider.description || 'Metadata provider';
  }

  function getConfigFields(providerName) {
    const fields = {};
    return fields[providerName] || [];
  }

  // --- Settings ---
  async function loadSettings() {
      try {
          const config = await getConfig();
          const meta = config.metadata_enhancement || {};
          confidenceThreshold = meta.confidence_threshold ?? 90;
          overwriteTags = meta.overwrite_tags ?? true;
          embedCoverArt = meta.embed_album_art ?? true;
          settingsLoaded = true;
      } catch (e) {
          console.error("Failed to load settings", e);
      }
  }

  async function saveSettings() {
      try {
          feedback.setLoading(true);
          const config = await getConfig();
          const updates = {
              metadata_enhancement: {
                  ...config.metadata_enhancement,
                  confidence_threshold: confidenceThreshold,
                  overwrite_tags: overwriteTags,
                  embed_album_art: embedCoverArt
              }
          };
          await setConfig(updates);
          feedback.addToast('Metadata settings saved', 'success');
      } catch (e) {
          feedback.addToast('Failed to save settings', 'error');
      } finally {
          feedback.setLoading(false);
      }
  }
</script>

<svelte:head>
  <title>Metadata Manager • Echosync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <h1>Metadata Manager</h1>
    <p class="subtitle">Manage metadata providers and enhancement settings.</p>
  </header>

  <div class="tabs">
      <button class="tab-btn active:scale-95 transition-all duration-200" class:active={activeTab === 'providers'} on:click={() => activeTab = 'providers'}>Providers</button>
      <button class="tab-btn active:scale-95 transition-all duration-200" class:active={activeTab === 'settings'} on:click={() => activeTab = 'settings'}>Settings</button>
  </div>

  <div class="tab-content">
      {#if activeTab === 'providers'}
          {#if loadError}
            <div class="error-card"><p>{loadError}</p></div>
          {:else if metadataProviders.length === 0}
            <div class="empty-state"><p class="muted">No metadata providers detected.</p></div>
          {:else}
            <div class="providers-grid">
              {#each metadataProviders as provider}
                <div class="provider-card">
                  <div class="provider-header">
                    <div class="provider-title">
                      <span class="provider-icon">{getProviderIcon(provider.name)}</span>
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
                  <p class="provider-description">{getProviderDescription(provider)}</p>
                  <div class="provider-config">
                    {#each getConfigFields(provider.name) as field}
                        <div class="config-field">
                          <label for="{provider.name}-{field.key}">{field.label}</label>
                          <div class="input-group">
                            <input
                              id="{provider.name}-{field.key}"
                              type={visibleFields[`${provider.name}-${field.key}`] ? 'text' : field.type}
                              placeholder={field.placeholder}
                              bind:value={providerConfigs[provider.name][field.key]}
                              class="config-input"
                            />
                            {#if field.type === 'password'}
                              <button
                                class="btn-toggle-visibility active:scale-95 transition-all duration-200"
                                on:click={() => visibleFields[`${provider.name}-${field.key}`] = !visibleFields[`${provider.name}-${field.key}`]}
                                type="button"
                                title={visibleFields[`${provider.name}-${field.key}`] ? 'Hide' : 'Show'}
                              >
                                {visibleFields[`${provider.name}-${field.key}`] ? 'Hide' : 'Show'}
                              </button>
                            {/if}
                            <button class="btn-save active:scale-95 transition-all duration-200" on:click={() => saveProviderCredentials(provider.name, providerConfigs[provider.name])} disabled={savingProvider === provider.name}>
                              {savingProvider === provider.name ? 'Saving...' : 'Save'}
                            </button>
                          </div>
                        </div>
                    {/each}
                  </div>
                </div>
              {/each}
            </div>
          {/if}

      {:else if activeTab === 'settings'}
          <div class="settings-card">
              <p class="text-sm text-slate-400">Settings are now automatically managed by the backend auto_importer engine.</p>
          </div>
      {/if}
  </div>
</section>

<style>
  .page { display: flex; flex-direction: column; gap: 20px; }
  .page__header h1 { margin: 0; font-size: 28px; }
  .subtitle { color: var(--muted); margin: 4px 0 0; }

  /* Tabs */
  .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
  .tab-btn {
      background: none; border: none; padding: 10px 20px; color: var(--muted); cursor: pointer; font-weight: 500;
      border-bottom: 2px solid transparent; display: flex; align-items: center; gap: 6px;
  }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

  /* Providers Styles */
  .providers-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(500px, 1fr)); gap: 16px; }
  .provider-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .provider-header { display: flex; justify-content: space-between; }
  .provider-title { display: flex; gap: 12px; }
  .provider-icon { font-size: 32px; }
  .provider-title h2 { margin: 0; font-size: 20px; }
  .badge { background: rgba(59, 130, 246, 0.1); color: #3b82f6; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
  .status-badge { padding: 4px 12px; border-radius: 6px; font-size: 13px; }
  .status-badge.configured { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
  .status-badge.not-configured { background: rgba(251, 191, 36, 0.1); color: #fbbf24; }
  .provider-description { color: var(--muted); margin: 0; }
  .provider-config { display: flex; flex-direction: column; gap: 16px; padding-top: 8px; border-top: 1px solid var(--border); }
  .input-group { display: flex; gap: 8px; }
  .config-input { flex: 1; padding: 8px; background: var(--input-bg); border: 1px solid var(--border); color: var(--text); border-radius: 4px; }
  .btn-save { padding: 8px 16px; background: var(--accent); color: white; border: none; border-radius: 4px; cursor: pointer; }

  /* Settings Styles */
  .settings-card { background: var(--card-bg); padding: 20px; border-radius: 8px; border: 1px solid var(--border); max-width: 600px; display: flex; flex-direction: column; gap: 20px; }

  .btn-toggle-visibility {
    padding: 10px 12px;
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }
  .btn-toggle-visibility:hover {
    background: var(--hover-bg, rgba(255, 255, 255, 0.05));
    border-color: var(--accent, #3b82f6);
    color: var(--accent, #3b82f6);
  }

  .loading, .empty-state { text-align: center; color: var(--muted); padding: 40px; }
  .muted { color: var(--muted); }
</style>
