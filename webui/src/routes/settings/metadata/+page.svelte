<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import { feedback } from '../../../stores/feedback';

  let metadataProviders = [];
  let loadError = '';
  let providerConfigs = {};
  let savingProvider = '';
  let visibleFields = {};  // Track which password fields are visible

  onMount(async () => {
    try {
      await providers.load();
      const allProviders = Object.values($providers?.items ?? []);
      
      console.log('All providers:', allProviders);
      console.log('Total providers:', allProviders.length);
      
      // Filter for metadata-capable providers
      metadataProviders = allProviders.filter(p => {
        const hasCapability = p.capabilities?.fetch_metadata || 
                             p.capabilities?.resolve_fingerprint ||
                             p.service_type === 'metadata';
        
        if (p.name === 'acoustid' || p.name === 'musicbrainz') {
          console.log(`Provider ${p.name}:`, {
            fetch_metadata: p.capabilities?.fetch_metadata,
            resolve_fingerprint: p.capabilities?.resolve_fingerprint,
            service_type: p.service_type,
            hasCapability
          });
        }
        
        return hasCapability;
      });

      console.log('Filtered metadata providers:', metadataProviders);

      // Load existing configs for each provider
      for (const provider of metadataProviders) {
        await loadProviderConfig(provider.name);
      }
    } catch (err) {
      loadError = 'Failed to load metadata providers. Check backend connection.';
      console.error(err);
    }
  });

  async function loadProviderConfig(providerName) {
    try {
      // Initialize config object if it doesn't exist
      if (!providerConfigs[providerName]) {
        providerConfigs[providerName] = {};
      }
      
      const response = await fetch(`/api/providers/${providerName}/credentials`);
      if (response.ok) {
        const data = await response.json();
        providerConfigs[providerName] = data.credentials || {};
      }
    } catch (err) {
      console.error(`Failed to load config for ${providerName}:`, err);
      // Ensure the config object exists even on error
      if (!providerConfigs[providerName]) {
        providerConfigs[providerName] = {};
      }
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
        await loadProviderConfig(providerName);
      } else {
        const error = await response.json();
        feedback.addToast(`Failed to save: ${error.error || 'Unknown error'}`, 'error');
      }
    } catch (err) {
      feedback.addToast(`Error saving ${providerName} credentials`, 'error');
      console.error(err);
    } finally {
      savingProvider = '';
      feedback.setLoading(false);
    }
  }

  function getProviderIcon(providerName) {
    const icons = {
      acoustid: '🔍',
      musicbrainz: '🎵'
    };
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
    // Define configuration fields for each provider
    const fields = {
      acoustid: [
        {
          key: 'api_key',
          label: 'API Key',
          type: 'password',
          placeholder: 'Enter your AcoustID API key',
          help: 'Get your free API key from https://acoustid.org/new-application',
          required: true,
          sensitive: true
        }
      ],
      musicbrainz: [
        // MusicBrainz doesn't require credentials (public API)
        {
          key: 'info',
          label: 'Information',
          type: 'info',
          value: 'MusicBrainz is a free public service and requires no configuration. Rate limiting (1 request/second) is automatically enforced.'
        }
      ]
    };
    return fields[providerName] || [];
  }
</script>

<svelte:head>
  <title>Metadata Providers • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <h1>Metadata Providers</h1>
    <p class="subtitle">Configure audio fingerprinting and metadata enrichment services</p>
  </header>

  {#if loadError}
    <div class="error-card">
      <p>{loadError}</p>
    </div>
  {:else if metadataProviders.length === 0}
    <div class="empty-state">
      <p class="muted">No metadata providers detected. Make sure the backend is running and providers are loaded.</p>
    </div>
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
                  {#if provider.capabilities?.resolve_fingerprint}
                    <span class="badge">Fingerprinting</span>
                  {/if}
                  {#if provider.capabilities?.fetch_metadata}
                    <span class="badge">Metadata</span>
                  {/if}
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
              {#if field.type === 'info'}
                <div class="info-box">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                  </svg>
                  <p>{field.value}</p>
                </div>
              {:else}
                <div class="config-field">
                  <label for="{provider.name}-{field.key}">
                    {field.label}
                    {#if field.required}
                      <span class="required">*</span>
                    {/if}
                  </label>
                  {#if field.help}
                    <p class="field-help">{field.help}</p>
                  {/if}
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
                        class="btn-toggle-visibility"
                        on:click={() => visibleFields[`${provider.name}-${field.key}`] = !visibleFields[`${provider.name}-${field.key}`]}
                        type="button"
                        title={visibleFields[`${provider.name}-${field.key}`] ? 'Hide' : 'Show'}
                      >
                        {#if visibleFields[`${provider.name}-${field.key}`]}
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </svg>
                        {:else}
                          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.26 3.64m-5.88-2.12a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </svg>
                        {/if}
                      </button>
                    {/if}
                    <button
                      class="btn-save"
                      on:click={() => saveProviderCredentials(provider.name, providerConfigs[provider.name])}
                      disabled={savingProvider === provider.name}
                    >
                      {savingProvider === provider.name ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>
              {/if}
            {/each}
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
    gap: 20px;
  }

  .page__header {
    margin-bottom: 8px;
  }

  .page__header h1 {
    margin: 0 0 8px 0;
    font-size: 28px;
    font-weight: 600;
  }

  .subtitle {
    margin: 0;
    color: var(--muted);
    font-size: 14px;
  }

  .providers-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
    gap: 16px;
  }

  .provider-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .provider-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .provider-title {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }

  .provider-icon {
    font-size: 32px;
    line-height: 1;
  }

  .provider-title h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    text-transform: capitalize;
  }

  .provider-type {
    margin: 4px 0 0 0;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    background: var(--accent-bg, rgba(59, 130, 246, 0.1));
    color: var(--accent, #3b82f6);
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .provider-status {
    flex-shrink: 0;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
  }

  .status-badge.configured {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }

  .status-badge.not-configured {
    background: rgba(251, 191, 36, 0.1);
    color: #fbbf24;
  }

  .provider-description {
    margin: 0;
    color: var(--muted);
    font-size: 14px;
    line-height: 1.5;
  }

  .provider-config {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-top: 8px;
    border-top: 1px solid var(--border);
  }

  .info-box {
    display: flex;
    gap: 12px;
    padding: 12px;
    background: rgba(59, 130, 246, 0.05);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 8px;
    color: var(--text-secondary);
  }

  .info-box svg {
    flex-shrink: 0;
    color: var(--accent, #3b82f6);
    margin-top: 2px;
  }

  .info-box p {
    margin: 0;
    font-size: 13px;
    line-height: 1.5;
  }

  .config-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .config-field label {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .required {
    color: #ef4444;
  }

  .field-help {
    margin: 0;
    font-size: 12px;
    color: var(--muted);
    line-height: 1.4;
  }

  .field-help a {
    color: var(--accent, #3b82f6);
    text-decoration: none;
  }

  .field-help a:hover {
    text-decoration: underline;
  }

  .input-group {
    display: flex;
    gap: 8px;
  }

  .config-input {
    flex: 1;
    padding: 10px 12px;
    background: var(--input-bg, #1a1a1a);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-primary);
    font-size: 14px;
    font-family: inherit;
  }

  .config-input:focus {
    outline: none;
    border-color: var(--accent, #3b82f6);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }

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

  .btn-toggle-visibility svg {
    width: 18px;
    height: 18px;
  }

  .btn-save {
    padding: 10px 20px;
    background: var(--accent, #3b82f6);
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .btn-save:hover:not(:disabled) {
    background: var(--accent-hover, #2563eb);
  }

  .btn-save:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .error-card {
    padding: 16px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 8px;
    color: #ef4444;
  }

  .empty-state {
    padding: 48px;
    text-align: center;
  }

  .muted {
    color: var(--muted);
  }
</style>
