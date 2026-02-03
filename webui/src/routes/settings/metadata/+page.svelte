<script>
  import { onMount } from 'svelte';
  import { providers } from '../../../stores/providers';
  import { feedback } from '../../../stores/feedback';
  import { getConfig, setConfig } from '../../../stores/config';
  import apiClient from '../../../api/client';
  import { metadataQueue } from '../../../stores/metadataQueue';

  // Tabs
  let activeTab = 'providers'; // providers, settings, queue, history

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

  // Queue Logic
  let queueItems = [];
  let queueLoading = false;
  let manualSearchModalOpen = false;
  let selectedTask = null;
  let manualSearchQuery = '';
  let manualSearchResults = [];
  let manualSearchLoading = false;

  // History Logic
  let historyItems = [];
  let historyLoading = false;

  onMount(async () => {
    // Initial Load
    await loadProviders();
    await loadSettings();
    metadataQueue.fetchCount(); // Update badge
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
        await loadProviderConfig(providerName);
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

  // --- Queue ---
  async function loadQueue() {
      queueLoading = true;
      try {
          const resp = await apiClient.get('/api/metadata/queue');
          queueItems = resp.data.queue || [];
      } catch (e) {
          console.error(e);
          feedback.addToast('Failed to load queue', 'error');
      } finally {
          queueLoading = false;
      }
  }

  async function approveTask(task, metadataOverride=null) {
      try {
          feedback.setLoading(true);
          await apiClient.post('/api/metadata/queue/approve', {
              id: task.id,
              metadata: metadataOverride || task.detected_metadata
          });
          feedback.addToast('Match approved', 'success');
          await loadQueue();
          metadataQueue.fetchCount();
          if (manualSearchModalOpen) manualSearchModalOpen = false;
      } catch (e) {
          feedback.addToast('Failed to approve match', 'error');
      } finally {
          feedback.setLoading(false);
      }
  }

  async function ignoreTask(task) {
       try {
          await apiClient.delete('/api/metadata/queue/ignore', {
              data: { id: task.id }
          });
          feedback.addToast('Task ignored', 'success');
          await loadQueue();
          metadataQueue.fetchCount();
      } catch (e) {
          feedback.addToast('Failed to ignore task', 'error');
      }
  }

  function openManualSearch(task) {
      selectedTask = task;
      manualSearchQuery = task.filename.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
      manualSearchResults = [];
      manualSearchModalOpen = true;
  }

  async function searchManual() {
      if (!manualSearchQuery) return;
      manualSearchLoading = true;
      try {
          const resp = await apiClient.post('/api/metadata/queue/manual-search', {
              query: manualSearchQuery
          });
          manualSearchResults = resp.data.results || [];
      } catch (e) {
          feedback.addToast('Search failed', 'error');
      } finally {
          manualSearchLoading = false;
      }
  }

  function closeManualSearch() {
      manualSearchModalOpen = false;
      selectedTask = null;
  }

  // --- History ---
  async function loadHistory() {
      historyLoading = true;
      try {
          const resp = await apiClient.get('/api/metadata/history');
          historyItems = resp.data.history || [];
      } catch (e) {
          feedback.addToast('Failed to load history', 'error');
      } finally {
          historyLoading = false;
      }
  }

  // Reactivity
  $: if (activeTab === 'queue') loadQueue();
  $: if (activeTab === 'history') loadHistory();

</script>

<svelte:head>
  <title>Metadata Manager • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <h1>Metadata Manager</h1>
    <p class="subtitle">Manage metadata providers, review queue, and history.</p>
  </header>

  <div class="tabs">
      <button class="tab-btn" class:active={activeTab === 'providers'} on:click={() => activeTab = 'providers'}>Providers</button>
      <button class="tab-btn" class:active={activeTab === 'settings'} on:click={() => activeTab = 'settings'}>Settings</button>
      <button class="tab-btn" class:active={activeTab === 'queue'} on:click={() => activeTab = 'queue'}>
        Review Queue
        {#if $metadataQueue.count > 0}
            <span class="tab-badge">{$metadataQueue.count}</span>
        {/if}
      </button>
      <button class="tab-btn" class:active={activeTab === 'history'} on:click={() => activeTab = 'history'}>History</button>
  </div>

  <div class="tab-content">
      {#if activeTab === 'providers'}
          <!-- Providers Tab Content (Existing Logic) -->
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
                      {#if field.type === 'info'}
                        <div class="info-box">
                          <p>{field.value}</p>
                        </div>
                      {:else}
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
                                class="btn-toggle-visibility"
                                on:click={() => visibleFields[`${provider.name}-${field.key}`] = !visibleFields[`${provider.name}-${field.key}`]}
                                type="button"
                                title={visibleFields[`${provider.name}-${field.key}`] ? 'Hide' : 'Show'}
                              >
                                {visibleFields[`${provider.name}-${field.key}`] ? 'Hide' : 'Show'}
                              </button>
                            {/if}
                            <button class="btn-save" on:click={() => saveProviderCredentials(provider.name, providerConfigs[provider.name])} disabled={savingProvider === provider.name}>
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

      {:else if activeTab === 'settings'}
          <!-- Settings Tab -->
          <div class="settings-card">
              <div class="field">
                  <label>Confidence Threshold: {confidenceThreshold}%</label>
                  <input type="range" min="50" max="100" bind:value={confidenceThreshold} />
                  <p class="help-text">Minimum confidence score required for auto-import.</p>
              </div>

              <div class="field-row">
                  <label class="switch-label">
                      <input type="checkbox" bind:checked={overwriteTags} />
                      <span class="label-text">Overwrite Existing Tags</span>
                  </label>
              </div>

              <div class="field-row">
                  <label class="switch-label">
                      <input type="checkbox" bind:checked={embedCoverArt} />
                      <span class="label-text">Embed Cover Art</span>
                  </label>
              </div>

              <button class="btn-primary" on:click={saveSettings}>Save Settings</button>
          </div>

      {:else if activeTab === 'queue'}
          <!-- Queue Tab -->
          {#if queueLoading}
              <div class="loading">Loading queue...</div>
          {:else if queueItems.length === 0}
              <div class="empty-state">No items in review queue.</div>
          {:else}
              <div class="queue-list">
                  {#each queueItems as item}
                      <div class="queue-item">
                          <div class="queue-info">
                              <div class="filename" title={item.file_path}>{item.filename}</div>
                              {#if item.detected_metadata}
                                  <div class="match-info">
                                      <span class="match-artist">{item.detected_metadata.artist}</span> -
                                      <span class="match-title">{item.detected_metadata.title}</span>
                                      <span class="match-score" class:low={item.confidence_score < 0.9}>
                                          {Math.round(item.confidence_score * 100)}% Match
                                      </span>
                                  </div>
                              {:else}
                                  <div class="no-match">No metadata detected</div>
                              {/if}
                          </div>
                          <div class="queue-actions">
                              {#if item.detected_metadata}
                                  <button class="btn-approve" on:click={() => approveTask(item)}>Approve</button>
                              {/if}
                              <button class="btn-manual" on:click={() => openManualSearch(item)}>Manual Search</button>
                              <button class="btn-ignore" on:click={() => ignoreTask(item)}>Ignore</button>
                          </div>
                      </div>
                  {/each}
              </div>
          {/if}

      {:else if activeTab === 'history'}
          <!-- History Tab -->
          {#if historyLoading}
              <div class="loading">Loading history...</div>
          {:else if historyItems.length === 0}
              <div class="empty-state">No history available.</div>
          {:else}
              <table class="history-table">
                  <thead>
                      <tr>
                          <th>Date</th>
                          <th>Filename</th>
                          <th>Status</th>
                          <th>Match</th>
                      </tr>
                  </thead>
                  <tbody>
                      {#each historyItems as item}
                          <tr>
                              <td>{new Date(item.created_at).toLocaleString()}</td>
                              <td title={item.file_path}>{item.filename}</td>
                              <td>
                                  <span class="status-pill {item.status}">{item.status}</span>
                              </td>
                              <td>
                                  {#if item.detected_metadata}
                                      {item.detected_metadata.artist} - {item.detected_metadata.title}
                                  {:else}
                                      -
                                  {/if}
                              </td>
                          </tr>
                      {/each}
                  </tbody>
              </table>
          {/if}
      {/if}
  </div>
</section>

<!-- Manual Search Modal -->
{#if manualSearchModalOpen}
    <div class="modal-overlay" on:click={closeManualSearch}>
        <div class="modal" on:click|stopPropagation>
            <h3>Manual Search</h3>
            <div class="search-box">
                <input type="text" bind:value={manualSearchQuery} on:keydown={(e) => e.key === 'Enter' && searchManual()} placeholder="Artist - Title or MBID" />
                <button on:click={searchManual}>Search</button>
            </div>

            <div class="search-results">
                {#if manualSearchLoading}
                    <div class="loading">Searching...</div>
                {:else}
                    {#each manualSearchResults as result}
                        <div class="result-item">
                            <div class="result-info">
                                <div><strong>{result.artist}</strong> - {result.title}</div>
                                <div class="muted">{result.album} ({result.year})</div>
                            </div>
                            <button class="btn-select" on:click={() => approveTask(selectedTask, result)}>Select</button>
                        </div>
                    {/each}
                {/if}
            </div>

            <button class="btn-close" on:click={closeManualSearch}>Close</button>
        </div>
    </div>
{/if}


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
  .tab-badge { background: #ef4444; color: white; font-size: 10px; padding: 1px 5px; border-radius: 10px; }

  /* Providers Styles (Recycled) */
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
  .field { display: flex; flex-direction: column; gap: 8px; }
  .field-row { display: flex; gap: 8px; align-items: center; }
  .switch-label { display: flex; gap: 8px; align-items: center; cursor: pointer; }
  .help-text { font-size: 12px; color: var(--muted); margin: 0; }
  .btn-primary { background: var(--accent); color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; align-self: flex-start; }

  /* Queue Styles */
  .queue-list { display: flex; flex-direction: column; gap: 12px; }
  .queue-item { background: var(--card-bg); border: 1px solid var(--border); padding: 16px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
  .filename { font-family: monospace; font-size: 13px; margin-bottom: 4px; word-break: break-all; }
  .match-info { font-size: 14px; }
  .match-artist { font-weight: 600; }
  .match-score { font-size: 12px; margin-left: 8px; color: #22c55e; font-weight: 500; }
  .match-score.low { color: #fbbf24; }
  .no-match { color: #ef4444; font-size: 13px; }
  .queue-actions { display: flex; gap: 8px; }
  .btn-approve { background: #22c55e; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
  .btn-manual { background: var(--accent); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
  .btn-ignore { background: transparent; border: 1px solid #ef4444; color: #ef4444; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
  .btn-ignore:hover { background: #ef4444; color: white; }

  /* History Styles */
  .history-table { width: 100%; border-collapse: collapse; }
  .history-table th { text-align: left; padding: 10px; border-bottom: 1px solid var(--border); color: var(--muted); font-weight: 500; }
  .history-table td { padding: 10px; border-bottom: 1px solid var(--border); font-size: 14px; }
  .status-pill { padding: 2px 8px; border-radius: 10px; font-size: 11px; text-transform: uppercase; font-weight: 600; }
  .status-pill.approved { background: rgba(34, 197, 94, 0.1); color: #22c55e; }
  .status-pill.ignored { background: rgba(107, 114, 128, 0.1); color: #6b7280; }

  /* Modal */
  .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: flex; justify-content: center; align-items: center; z-index: 100; }
  .modal { background: var(--card-bg); padding: 24px; border-radius: 12px; width: 500px; max-width: 90%; max-height: 80vh; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; border: 1px solid var(--border); }
  .modal h3 { margin: 0; }
  .search-box { display: flex; gap: 8px; }
  .search-box input { flex: 1; padding: 8px; border: 1px solid var(--border); border-radius: 4px; background: var(--input-bg); color: var(--text); }
  .search-results { display: flex; flex-direction: column; gap: 8px; max-height: 300px; overflow-y: auto; }
  .result-item { padding: 10px; border: 1px solid var(--border); border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }
  .result-info { font-size: 13px; }
  .btn-select { background: var(--accent); color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  .btn-close { align-self: flex-end; background: none; border: none; color: var(--muted); cursor: pointer; }

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

  .loading, .empty-state { text-align: center; color: var(--muted); padding: 40px; }
  .muted { color: var(--muted); }
</style>
