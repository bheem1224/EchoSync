<script>
  import { onMount } from 'svelte';
  import { providers } from '../../stores/providers';
  import { jobs } from '../../stores/jobs';
  import apiClient from '../../api/client';

  let sourceProvider = '';
  let targetProviders = [];
  let playlists = [];
  let selectedPlaylists = [];
  let loadingPlaylists = false;
  let syncing = false;
  let error = '';
  let success = '';

  $: playlistProviders = Object.values($providers.items).filter(p => 
    (p.capabilities?.supports_playlists ?? 'NONE') !== 'NONE'
  );

  $: syncTargets = Object.values($providers.items).filter(p => 
    p.capabilities?.supports_sync || p.capabilities?.server
  );

  async function loadPlaylists() {
    if (!sourceProvider) return;
    
    loadingPlaylists = true;
    error = '';
    playlists = [];
    
    try {
      const response = await apiClient.get(`/providers/${sourceProvider}/playlists`);
      playlists = response.data.items || [];
    } catch (err) {
      error = `Failed to load playlists: ${err.response?.data?.error || err.message}`;
    } finally {
      loadingPlaylists = false;
    }
  }

  async function startSync() {
    if (!sourceProvider || targetProviders.length === 0 || selectedPlaylists.length === 0) {
      error = 'Please select a source, at least one target, and at least one playlist.';
      return;
    }

    syncing = true;
    error = '';
    success = '';

    try {
      const response = await apiClient.post('/api/playlists/sync', {
        mode: 'provider-to-provider',
        sources: [sourceProvider],
        targets: {
          providers: targetProviders,
          libraries: []
        },
        playlists: selectedPlaylists
      });

      if (response.data.accepted) {
        success = 'Sync job created successfully!';
        selectedPlaylists = [];
        // Refresh jobs store to show the new job
        jobs.load();
      } else {
        error = response.data.error || 'Failed to start sync.';
      }
    } catch (err) {
      error = `Error starting sync: ${err.response?.data?.error || err.message}`;
    } finally {
      syncing = false;
    }
  }

  function togglePlaylist(id) {
    if (selectedPlaylists.includes(id)) {
      selectedPlaylists = selectedPlaylists.filter(i => i !== id);
    } else {
      selectedPlaylists = [...selectedPlaylists, id];
    }
  }

  function toggleTarget(id) {
    if (targetProviders.includes(id)) {
      targetProviders = targetProviders.filter(i => i !== id);
    } else {
      targetProviders = [...targetProviders, id];
    }
  }

  onMount(() => {
    providers.load();
  });
</script>

<svelte:head>
  <title>Sync • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div>
      <p class="eyebrow">Operations</p>
      <h1>Sync Playlists</h1>
      <p class="sub">Transfer and synchronize playlists between services.</p>
    </div>
  </header>

  <div class="sync-container">
    <div class="setup-grid">
      <!-- Step 1: Source -->
      <div class="card">
        <div class="card__header">
          <span class="step-num">1</span>
          <h2>Source Service</h2>
        </div>
        <div class="form-group">
          <label for="source">Select where to sync from:</label>
          <select id="source" bind:value={sourceProvider} on:change={loadPlaylists}>
            <option value="">-- Select Source --</option>
            {#each playlistProviders as p}
              <option value={p.id}>{p.name}</option>
            {/each}
          </select>
        </div>
      </div>

      <!-- Step 2: Targets -->
      <div class="card">
        <div class="card__header">
          <span class="step-num">2</span>
          <h2>Target Services</h2>
        </div>
        <div class="targets-list">
          {#each syncTargets as p}
            {#if p.id !== sourceProvider}
              <label class="target-item">
                <input type="checkbox" 
                       checked={targetProviders.includes(p.id)} 
                       on:change={() => toggleTarget(p.id)} />
                <span class="target-name">{p.name}</span>
                <span class="target-type">{p.capabilities?.server ? 'Server' : 'Sync'}</span>
              </label>
            {/if}
          {/each}
          {#if syncTargets.length === 0}
            <p class="muted">No target services available.</p>
          {/if}
        </div>
      </div>
    </div>

    <!-- Step 3: Playlists -->
    <div class="card playlists-card">
      <div class="card__header">
        <span class="step-num">3</span>
        <h2>Select Playlists</h2>
        {#if selectedPlaylists.length > 0}
          <span class="badge">{selectedPlaylists.length} selected</span>
        {/if}
      </div>

      {#if !sourceProvider}
        <div class="empty-state">
          <p class="muted">Select a source service to view playlists.</p>
        </div>
      {:else if loadingPlaylists}
        <div class="empty-state">
          <div class="spinner"></div>
          <p>Loading playlists...</p>
        </div>
      {:else if playlists.length === 0}
        <div class="empty-state">
          <p class="muted">No playlists found for this provider.</p>
        </div>
      {:else}
        <div class="playlists-grid">
          {#each playlists as playlist}
            <button class="playlist-item" 
                    class:selected={selectedPlaylists.includes(playlist.id)}
                    on:click={() => togglePlaylist(playlist.id)}>
              <div class="playlist-info">
                <strong>{playlist.name}</strong>
                {#if playlist.track_count !== undefined}
                  <span class="muted small">{playlist.track_count} tracks</span>
                {/if}
              </div>
              <div class="checkbox">
                {#if selectedPlaylists.includes(playlist.id)}
                  <svg viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                  </svg>
                {/if}
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="actions">
      {#if error}
        <p class="error-msg">{error}</p>
      {/if}
      {#if success}
        <p class="success-msg">{success}</p>
      {/if}
      <button class="btn btn--primary" 
              disabled={syncing || !sourceProvider || targetProviders.length === 0 || selectedPlaylists.length === 0}
              on:click={startSync}>
        {#if syncing}
          Starting Sync...
        {:else}
          Start Synchronization
        {/if}
      </button>
    </div>
  </div>
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .sync-container {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .setup-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  @media (max-width: 800px) {
    .setup-grid {
      grid-template-columns: 1fr;
    }
  }

  .card {
    background: var(--glass);
    backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
    padding: 20px;
  }

  .card__header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }

  .step-num {
    width: 24px;
    height: 24px;
    background: var(--accent);
    color: #000;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 800;
    font-size: 12px;
  }

  .card__header h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  select {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px;
    color: #fff;
    font-size: 14px;
    outline: none;
  }

  select:focus {
    border-color: var(--accent);
  }

  .targets-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .target-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s;
  }

  .target-item:hover {
    background: rgba(255, 255, 255, 0.06);
  }

  .target-name {
    flex: 1;
    font-size: 14px;
    font-weight: 500;
  }

  .target-type {
    font-size: 10px;
    text-transform: uppercase;
    background: rgba(255, 255, 255, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
    color: #94a3b8;
  }

  .playlists-card {
    min-height: 300px;
  }

  .playlists-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 12px;
  }

  .playlist-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s;
    color: inherit;
    font-family: inherit;
  }

  .playlist-item:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.1);
  }

  .playlist-item.selected {
    background: rgba(15, 239, 136, 0.05);
    border-color: var(--accent);
  }

  .playlist-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .checkbox {
    width: 20px;
    height: 20px;
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
  }

  .selected .checkbox {
    border-color: var(--accent);
    background: var(--accent);
    color: #000;
  }

  .actions {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 14px;
  }

  .btn--primary {
    background: var(--accent);
    color: #000;
    padding: 12px 32px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 16px;
    border: none;
    cursor: pointer;
    transition: transform 0.2s, opacity 0.2s;
  }

  .btn--primary:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(15, 239, 136, 0.3);
  }

  .btn--primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-msg { color: #ef4444; font-size: 14px; }
  .success-msg { color: var(--accent); font-size: 14px; font-weight: 600; }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    color: #94a3b8;
  }

  .spinner {
    width: 30px;
    height: 30px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .badge {
    background: var(--accent);
    color: #000;
    border-radius: 6px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
  }

  .muted { color: #94a3b8; }
  .small { font-size: 12px; }
</style>
