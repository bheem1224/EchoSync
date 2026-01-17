<script>
  import { onMount } from 'svelte';
  import { providers } from '../../stores/providers';
  import { jobs } from '../../stores/jobs';
  import { preferences } from '../../stores/preferences';
  import apiClient from '../../api/client';

  let sourceProvider = '';
  let targetProvider = '';
  let playlists = [];
  let selectedPlaylists = [];
  let loadingPlaylists = false;
  let syncing = false;
  let error = '';
  let success = '';

  // Analysis modal state
  let analysisModalOpen = false;
  let analysisLoading = false;
  let analysisError = '';
  let analysisResult = null;
  let analysisStarted = false;
  let downloadingMissing = false;
  let selectedQuality = '';
  
  // Sync config modal state
  let syncConfigModalOpen = false;
  let syncInProgress = false;
  let syncDownloadMissing = false;
  
  // Sync progress modal state
  let syncProgressModalOpen = false;
  let syncEventStream = [];
  let syncProgressEvent = null;
  let syncEventPollingId = null;
  
  // Scheduled syncs state
  let scheduledSyncs = [];
  let showScheduleModal = false;
  let scheduleForm = {
    source: '',
    target: '',
    playlists: [],
    interval: 3600,
    download_missing: false,
  };
  let scheduleIntervalOptions = [
    { value: 300, label: '5 minutes' },
    { value: 900, label: '15 minutes' },
    { value: 1800, label: '30 minutes' },
    { value: 3600, label: '1 hour' },
    { value: 21600, label: '6 hours' },
    { value: 43200, label: '12 hours' },
    { value: 86400, label: '24 hours' },
    { value: 604800, label: '1 week' },
  ];

  $: qualityProfiles = $preferences.profiles || [];
  $: if (qualityProfiles.length > 0 && !selectedQuality) {
    selectedQuality = qualityProfiles[0]?.name || '';
  }

  $: playlistProviders = Object.values($providers.items).filter(p => 
    (p.capabilities?.supports_playlists ?? 'NONE') !== 'NONE'
  );

  $: syncTargets = Object.values($providers.items).filter(p => 
    // Streaming services (Spotify, Tidal) OR Media servers (Plex, Jellyfin, Navidrome)
    (p.capabilities?.supports_playlists === 'READ_WRITE') || 
    (p.capabilities?.supports_library_scan ?? false)
  );

  async function loadPlaylists() {
    if (!sourceProvider) {
      console.log('[Sync] No source provider selected');
      return;
    }

    loadingPlaylists = true;
    error = '';
    playlists = [];

    try {
      console.log(`[Sync] Loading playlists for provider: ${sourceProvider}`);
      const response = await apiClient.get(`/providers/${sourceProvider}/playlists`);
      console.log('[Sync] Full response object:', response);
      console.log('[Sync] Response data:', response.data);
      console.log('[Sync] Response data type:', typeof response.data);
      console.log('[Sync] Response data.items:', response.data.items);

      playlists = response.data.items || [];
      console.log('[Sync] Playlists after assignment:', playlists);
      console.log('[Sync] Number of playlists:', playlists.length);
    } catch (err) {
      console.error('[Sync] Error loading playlists:', err);
      error = `Failed to load playlists: ${err.response?.data?.error || err.message}`;
    } finally {
      loadingPlaylists = false;
    }
  }

  async function runAnalysis() {
    if (!sourceProvider || !targetProvider || selectedPlaylists.length === 0) {
      analysisError = 'Select a source, target, and at least one playlist to analyze.';
      return;
    }
    analysisLoading = true;
    analysisError = '';
    analysisResult = null;
    analysisStarted = true;

    try {
      const selectedDetails = playlists
        .filter(p => selectedPlaylists.includes(p.id))
        .map(p => ({ id: p.id, name: p.name, track_count: p.track_count }));

      const response = await apiClient.post('/playlists/analyze', {
        source: sourceProvider,
        target: targetProvider,
        quality_profile: selectedQuality,
        playlists: selectedDetails
      });
      analysisResult = response.data;
    } catch (err) {
      console.error('[Sync] Analysis error:', err);
      analysisError = err.response?.data?.error || err.message || 'Analysis failed';
    } finally {
      analysisLoading = false;
    }
  }

  async function downloadMissingTracks() {
    if (!analysisResult || downloadingMissing) return;
    downloadingMissing = true;
    error = '';
    success = '';

    try {
      const response = await apiClient.post('/playlists/download-missing', {
        missing: analysisResult.missing || []
      });

      if (response.data.accepted) {
        success = 'Download job created. Check Jobs for progress.';
        jobs.load();
      } else {
        error = response.data.error || 'Failed to start download job.';
      }
    } catch (err) {
      error = err.response?.data?.error || err.message || 'Download failed';
    } finally {
      downloadingMissing = false;
    }
  }
  
  function openSyncConfigModal() {
    if (!analysisResult?.summary?.can_sync) {
      analysisError = 'No matched tracks to sync.';
      return;
    }
    syncConfigModalOpen = true;
  }
  
  function closeSyncConfigModal() {
    syncConfigModalOpen = false;
  }
  
  async function confirmSync() {
    if (!analysisResult?.summary?.matched_pairs) return;
    syncInProgress = true;
    analysisError = '';
    
    try {
      const response = await apiClient.post('/playlists/sync', {
        source: sourceProvider,
        target_source: targetProvider,
        playlist_name: selectedPlaylists.length === 1 
          ? playlists.find(p => p.id === selectedPlaylists[0])?.name || 'Synced Playlist'
          : 'Multi-Playlist Sync',
        matches: analysisResult.summary.matched_pairs,
        download_missing: syncDownloadMissing
      });
      
      if (response.data.accepted) {
        syncConfigModalOpen = false;
        syncProgressModalOpen = true;
        // Fix the events_path - remove /api prefix if present since client already adds it
        const eventsPath = response.data.events_path?.startsWith('/api') 
          ? response.data.events_path.substring(4)
          : response.data.events_path;
        startSyncEventPolling(response.data.job, eventsPath);
      } else {
        analysisError = response.data.error || 'Sync failed to start';
      }
    } catch (err) {
      analysisError = err.response?.data?.error || err.message || 'Sync failed';
    } finally {
      syncInProgress = false;
    }
  }
  
  function startSyncEventPolling(jobName, eventsPath) {
    syncEventStream = [];
    let lastEventId = -1;
    
    const pollEvents = async () => {
      try {
        const separator = eventsPath.includes('?') ? '&' : '?';
        const url = `${eventsPath}${separator}since=${lastEventId}`;
        const response = await apiClient.get(url);
        const newEvents = response.data.events || [];
        
        syncEventStream = [...syncEventStream, ...newEvents];
        
        if (newEvents.length > 0) {
          lastEventId = newEvents[newEvents.length - 1].id;
          syncProgressEvent = newEvents[newEvents.length - 1];
          
          if (syncProgressEvent.type === 'sync_complete') {
            clearInterval(syncEventPollingId);
            syncEventPollingId = null;
            setTimeout(() => {
              jobs.load();
              // Auto-download if checkbox was checked
              if (syncDownloadMissing) {
                closeSyncProgressModal();
                downloadMissingTracks();
              } else {
                success = 'Sync completed!';
              }
            }, 500);
          } else if (syncProgressEvent.type === 'sync_error') {
            clearInterval(syncEventPollingId);
            syncEventPollingId = null;
          }
        }
      } catch (err) {
        console.error('Event polling error:', err);
      }
    };
    
    pollEvents();
    syncEventPollingId = setInterval(pollEvents, 500);
  }
  
  function closeSyncProgressModal() {
    if (syncEventPollingId) {
      clearInterval(syncEventPollingId);
      syncEventPollingId = null;
    }
    syncProgressModalOpen = false;
    syncEventStream = [];
    syncProgressEvent = null;
  }
  
  async function loadScheduledSyncs() {
    try {
      const response = await apiClient.get('/playlists/sync/scheduled');
      scheduledSyncs = response.data.scheduled_syncs || [];
    } catch (err) {
      console.error('Failed to load scheduled syncs:', err);
    }
  }
  
  function openScheduleModal() {
    scheduleForm = {
      source: sourceProvider,
      target: targetProvider,
      playlists: selectedPlaylists,
      interval: 3600,
      download_missing: false,
    };
    showScheduleModal = true;
  }
  
  function closeScheduleModal() {
    showScheduleModal = false;
  }
  
  async function createScheduledSync() {
    try {
      const response = await apiClient.post('/playlists/sync/schedule', {
        source: scheduleForm.source,
        target_source: scheduleForm.target,
        playlists: scheduleForm.playlists,
        interval: scheduleForm.interval,
        download_missing: scheduleForm.download_missing,
      });
      
      if (response.data.accepted) {
        success = `Scheduled sync created! Runs every ${scheduleIntervalOptions.find(o => o.value === scheduleForm.interval)?.label || scheduleForm.interval + 's'}.`;
        closeScheduleModal();
        loadScheduledSyncs();
      }
    } catch (err) {
      error = err.response?.data?.error || err.message || 'Failed to create scheduled sync';
    }
  }
  
  async function deleteScheduledSync(syncId) {
    if (!confirm('Delete this scheduled sync?')) return;
    try {
      await apiClient.delete(`/playlists/sync/scheduled/${syncId}`);
      success = 'Scheduled sync deleted.';
      loadScheduledSyncs();
    } catch (err) {
      error = err.response?.data?.error || err.message || 'Failed to delete scheduled sync';
    }
  }

  function openAnalysisModal() {
    if (!sourceProvider || !targetProvider || selectedPlaylists.length === 0) {
      error = 'Please select a source, target, and at least one playlist.';
      return;
    }
    analysisModalOpen = true;
    runAnalysis();
  }

  function closeAnalysisModal() {
    analysisModalOpen = false;
    analysisResult = null;
    analysisError = '';
    analysisStarted = false;
  }

  async function startSync() {
    // retain existing direct sync as a fallback (not used by UI now)
    return openAnalysisModal();
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
    preferences.load();
    loadScheduledSyncs();
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
          <select id="source" bind:value={sourceProvider} on:change={() => {
              console.log('[Debug] Source provider selected:', sourceProvider);
              loadPlaylists();
            }}>
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
        <div class="form-group">
          <label for="target">Select sync target:</label>
          <select id="target" bind:value={targetProvider}>
            <option value="">-- Select Target --</option>
            {#each syncTargets as p}
              {#if p.id !== sourceProvider}
                <option value={p.id}>{p.name}</option>
              {/if}
            {/each}
          </select>
          {#if syncTargets.length === 0}
            <p class="muted small">No target services available.</p>
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
              disabled={syncing || !sourceProvider || !targetProvider || selectedPlaylists.length === 0}
              on:click={openAnalysisModal}>
        {#if syncing}
          Preparing...
        {:else}
          Sync Playlist
        {/if}
      </button>
      <button type="button" class="btn btn--secondary" on:click={openScheduleModal}>
        ⏰ Create Schedule
      </button>
    </div>
  </div>

  <!-- Scheduled Syncs Section -->
  <div class="scheduled-syncs-section">
    <div class="section-header">
      <h2>Scheduled Syncs</h2>
      <button type="button" class="btn btn--accent" on:click={openScheduleModal}>
        + Create Schedule
      </button>
    </div>
    
    {#if scheduledSyncs.length > 0}
      <div class="syncs-table">
        <div class="table-header">
          <div class="col-source">Source</div>
          <div class="col-target">Target</div>
          <div class="col-interval">Interval</div>
          <div class="col-playlists">Playlists</div>
          <div class="col-actions">Actions</div>
        </div>
        {#each scheduledSyncs as sync (sync.id)}
          <div class="table-row">
            <div class="col-source">{sync.source}</div>
            <div class="col-target">{sync.target}</div>
            <div class="col-interval">
              {scheduleIntervalOptions.find(o => o.value === sync.interval)?.label || sync.interval + 's'}
            </div>
            <div class="col-playlists">{sync.playlists.length}</div>
            <div class="col-actions">
              <button type="button" class="btn btn--small" on:click={() => deleteScheduledSync(sync.id)}>
                Delete
              </button>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <p class="empty-state">No scheduled syncs yet. Create one to automate your playlists!</p>
    {/if}
  </div>
</section>

{#if analysisModalOpen}
  <div class="modal-backdrop" on:click={closeAnalysisModal}></div>
  <div class="modal">
    <header class="modal__header">
      <div>
        <p class="eyebrow">Playlist Sync</p>
        <h2>Analysis</h2>
        <p class="sub">Source: {sourceProvider} → Target: {targetProvider}</p>
      </div>
      <button class="close-btn" on:click={closeAnalysisModal}>×</button>
    </header>

    <div class="modal__body">
      <div class="summary-grid">
        <div class="summary-card">
          <div class="label">Total Tracks</div>
          <div class="value">{analysisResult?.summary?.total_tracks ?? '–'}</div>
        </div>
        <div class="summary-card">
          <div class="label">Found in Library</div>
          <div class="value">{analysisResult?.summary?.found_in_library ?? '–'}</div>
        </div>
        <div class="summary-card">
          <div class="label">Missing</div>
          <div class="value highlight">{analysisResult?.summary?.missing_tracks ?? '–'}</div>
        </div>
        <div class="summary-card">
          <div class="label">Downloaded</div>
          <div class="value">{analysisResult?.summary?.downloaded ?? 0}</div>
        </div>
      </div>

      <div class="controls-row">
        <div class="control">
          <label>Quality Profile</label>
          <select bind:value={selectedQuality}>
            {#if qualityProfiles.length === 0}
              <option value="">No profiles configured</option>
            {:else}
              {#each qualityProfiles as profile}
                <option value={profile.name}>{profile.name}</option>
              {/each}
            {/if}
          </select>
        </div>
        <div class="control buttons">
          <button class="btn" on:click={runAnalysis} disabled={analysisLoading}>
            {analysisLoading ? 'Analyzing…' : (analysisStarted ? 'Re-run Analysis' : 'Begin Analysis')}
          </button>
          <button class="btn btn--accent" on:click={openSyncConfigModal}
            disabled={!analysisResult?.summary?.can_sync}>
            ⇄ Sync
          </button>
          <button class="btn btn--primary" on:click={downloadMissingTracks}
            disabled={!analysisResult || downloadingMissing || (analysisResult?.summary?.missing_tracks ?? 0) === 0}>
            {downloadingMissing ? 'Starting…' : 'Download Missing Tracks'}
          </button>
        </div>
      </div>

      {#if analysisError}
        <p class="error-msg">{analysisError}</p>
      {/if}

      <div class="tracks-table-wrapper">
        <div class="tracks-table">
          <div class="table-header">
            <span>#</span>
            <span>Track</span>
            <span>Artist</span>
            <span>Duration</span>
            <span>Match Quality</span>
            <span>Download Status</span>
          </div>
          {#if analysisLoading}
            <div class="table-row muted">Analyzing tracks…</div>
          {:else if analysisResult?.tracks?.length}
            {#each analysisResult.tracks as track, idx}
              <div class="table-row">
                <span>{idx + 1}</span>
                <span title={track.title}>{track.title}</span>
                <span title={track.artist}>{track.artist}</span>
                <span>{track.duration || '–'}</span>
                <span class="match-badge {track.library_match?.includes('score') ? 'partial' : track.library_match === 'Found' ? 'found' : track.library_match?.includes('fuzzy') ? 'fuzzy' : 'missing'}">{track.library_match ?? 'Checking…'}</span>
                <span>{track.download_status ?? '-'}</span>
              </div>
            {/each}
          {:else}
            <div class="table-row muted">No track details available yet.</div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Sync Config Modal -->
{#if syncConfigModalOpen}
  <div class="modal-backdrop" role="presentation"></div>
  <div class="modal sync-config-modal">
    <div class="modal-header">
      <h2>Configure Sync</h2>
      <button type="button" class="close-btn" on:click={closeSyncConfigModal}>✕</button>
    </div>
    
    <div class="modal-body">
      <div class="config-summary">
        <div class="config-row">
          <span class="config-label">Source:</span>
          <span class="config-value">{sourceProvider}</span>
        </div>
        <div class="config-row">
          <span class="config-label">Target:</span>
          <span class="config-value">{targetProvider}</span>
        </div>
        <div class="config-row">
          <span class="config-label">Playlists:</span>
          <span class="config-value">{selectedPlaylists.length} selected</span>
        </div>
        <div class="config-row">
          <span class="config-label">Matched Tracks:</span>
          <span class="config-value">{analysisResult?.summary?.matched_pairs?.length || 0}</span>
        </div>
        <div class="config-row">
          <span class="config-label">Missing Tracks:</span>
          <span class="config-value">{analysisResult?.summary?.missing_tracks || 0}</span>
        </div>
      </div>
      
      <div class="config-options">
        <label>
          <input type="checkbox" bind:checked={syncDownloadMissing} />
          Download missing tracks after sync
        </label>
      </div>
    </div>
    
    <div class="modal-footer">
      <button type="button" class="btn" on:click={closeSyncConfigModal}>Cancel</button>
      <button type="button" class="btn btn--accent" on:click={confirmSync} disabled={syncInProgress}>
        {syncInProgress ? 'Starting Sync…' : 'Start Sync'}
      </button>
    </div>
  </div>
{/if}

<!-- Sync Progress Modal -->
{#if syncProgressModalOpen}
  <div class="modal-backdrop" role="presentation"></div>
  <div class="modal sync-progress-modal">
    <div class="modal-header">
      <h2>Sync Progress</h2>
      <button type="button" class="close-btn" on:click={closeSyncProgressModal}>✕</button>
    </div>
    
    <div class="modal-body progress-container">
      {#if syncProgressEvent}
        <div class="progress-state">
          <div class="state-badge {syncProgressEvent.type === 'sync_complete' ? 'complete' : syncProgressEvent.type === 'sync_error' ? 'error' : 'in-progress'}">
            {syncProgressEvent.type === 'sync_complete' ? '✓ Complete' : 
             syncProgressEvent.type === 'sync_error' ? '✗ Error' : 
             '⟳ In Progress'}
          </div>
          {#if syncProgressEvent.data?.message}
            <p class="state-message">{syncProgressEvent.data.message}</p>
          {/if}
        </div>
        
        <!-- Statistics Row -->
        {#if syncProgressEvent.data?.analysis}
          <div class="stats-row">
            <div class="stat">
              <span class="stat-label">Total</span>
              <span class="stat-value">{syncProgressEvent.data.analysis.total_tracks || 0}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Found</span>
              <span class="stat-value">{syncProgressEvent.data.analysis.found_count || 0}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Missing</span>
              <span class="stat-value">{syncProgressEvent.data.analysis.missing_count || 0}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Downloaded</span>
              <span class="stat-value">{syncProgressEvent.data.analysis.downloaded_count || 0}</span>
            </div>
          </div>
          
          <!-- Progress Bar -->
          {#if syncProgressEvent.data.analysis.total_tracks > 0}
            <div class="progress-bar-container">
              <div class="progress-label">Progress: {Math.round((syncProgressEvent.data.analysis.downloaded_count || 0) / (syncProgressEvent.data.analysis.total_tracks || 1) * 100)}%</div>
              <div class="progress-bar">
                <div class="progress-fill" style="width: {Math.round((syncProgressEvent.data.analysis.downloaded_count || 0) / (syncProgressEvent.data.analysis.total_tracks || 1) * 100)}%"></div>
              </div>
            </div>
          {/if}
        {/if}
      {/if}
      
      <div class="progress-timeline">
        {#each syncEventStream as event (event.id)}
          <div class="timeline-item event-{event.type}">
            <div class="timeline-marker">
              {#if event.type === 'track_synced'}
                ✓
              {:else if event.type === 'track_failed'}
                ✗
              {:else}
                •
              {/if}
            </div>
            <div class="timeline-content">
              <div class="timeline-type">{event.type.replace(/_/g, ' ')}</div>
              {#if event.data?.track_name}
                <div class="timeline-detail">{event.data.track_name}</div>
              {/if}
              {#if event.data?.error}
                <div class="timeline-error">{event.data.error}</div>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}

<!-- Schedule Modal -->
{#if showScheduleModal}
  <div class="modal-backdrop" role="presentation"></div>
  <div class="modal schedule-modal">
    <div class="modal-header">
      <h2>Create Scheduled Sync</h2>
      <button type="button" class="close-btn" on:click={closeScheduleModal}>✕</button>
    </div>
    
    <div class="modal-body">
      <div class="form-group">
        <label for="schedule-source">Source Service:</label>
        <select id="schedule-source" bind:value={scheduleForm.source}>
          {#each playlistProviders as p}
            <option value={p.id}>{p.name}</option>
          {/each}
        </select>
      </div>
      
      <div class="form-group">
        <label for="schedule-target">Target Service:</label>
        <select id="schedule-target" bind:value={scheduleForm.target}>
          {#each syncTargets as p}
            <option value={p.id}>{p.name}</option>
          {/each}
        </select>
      </div>
      
      <div class="form-group">
        <label for="schedule-interval">Repeat Interval:</label>
        <select id="schedule-interval" bind:value={scheduleForm.interval}>
          {#each scheduleIntervalOptions as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      </div>
      
      <div class="form-group">
        <label>
          <input type="checkbox" bind:checked={scheduleForm.download_missing} />
          Download missing tracks after sync
        </label>
      </div>
      
      <p class="info-text">Note: This will sync {scheduleForm.playlists.length} selected playlist(s) every {scheduleIntervalOptions.find(o => o.value === scheduleForm.interval)?.label || scheduleForm.interval + 's'}.</p>
    </div>
    
    <div class="modal-footer">
      <button type="button" class="btn" on:click={closeScheduleModal}>Cancel</button>
      <button type="button" class="btn btn--accent" on:click={createScheduledSync}>Create Schedule</button>
    </div>
  </div>
{/if}

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
    color: var(--text);
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .form-group label {
    color: var(--text);
    font-size: 14px;
    font-weight: 500;
  }

  select {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 12px 16px;
    color: var(--text);
    font-size: 14px;
    outline: none;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23ffffff' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 36px;
  }

  select option {
    background: #1a1a1a;
    color: var(--text);
    padding: 8px;
  }

  select:hover {
    border-color: rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.08);
  }

  select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(15, 239, 136, 0.1);
  }

  .playlists-grid {    padding: 2px 6px;
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
    color: var(--text);
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

  .btn, .btn--primary {
    background: var(--accent);
    color: #000;
    padding: 12px 24px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 14px;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text);
  }

  .btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.12);
    transform: translateY(-1px);
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

  /* Analysis modal */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.55);
    backdrop-filter: blur(4px);
    z-index: 20;
  }
  .modal {
    position: fixed;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: min(1100px, 96vw);
    max-height: 90vh;
    background: rgba(10, 10, 10, 0.98);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 24px;
    z-index: 30;
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow: hidden;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  }
  .modal__header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding-bottom: 16px;
  }

  .modal__header h2 {
    color: var(--text);
    margin: 0;
  }

  .modal__header .eyebrow {
    color: var(--accent);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 0 0 4px 0;
  }

  .modal__header .sub {
    color: var(--muted);
    font-size: 13px;
    margin: 4px 0 0 0;
  }
  .modal__body {
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow: auto;
  }
  .close-btn {
    background: rgba(255, 255, 255, 0.05);
    border: none;
    color: var(--muted);
    font-size: 24px;
    cursor: pointer;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }

  .close-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text);
  }
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
  }
  .summary-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 12px;
    padding: 12px;
  }
  .summary-card .label { color: var(--muted); font-size: 12px; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
  .summary-card .value { font-size: 24px; font-weight: 700; color: var(--text); }
  .summary-card .highlight { color: #fbbf24; }

  .controls-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
  }
  .control { display: flex; flex-direction: column; gap: 6px; }
  .control label { color: var(--text); font-size: 13px; font-weight: 500; }
  .control.buttons { flex-direction: row; align-items: center; gap: 10px; }
  .controls-row select {
    min-width: 180px;
  }
  .tracks-table-wrapper {
    max-height: 450px;
    overflow-y: auto;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    margin-top: 1.5rem;
  }

  .tracks-table {
    width: 100%;
  }

  .table-header {
    position: sticky;
    top: 0;
    background: rgba(15, 23, 42, 0.95);
    z-index: 10;
  }

  .table-row {
    display: grid;
    grid-template-columns: 40px 1.5fr 1.2fr 90px 140px 160px;
    gap: 8px;
    padding: 10px 12px;
    align-items: center;
  }

  .table-row span {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .match-badge {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }

  .match-badge.found {
    background: rgba(74, 222, 128, 0.1);
    color: #4ade80;
  }

  .match-badge.fuzzy {
    background: rgba(250, 204, 21, 0.1);
    color: #facc15;
  }

  .match-badge.partial {
    background: rgba(96, 165, 250, 0.1);
    color: #60a5fa;
  }

  .match-badge.missing {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }

  /* Sync Config Modal */
  .sync-config-modal {
    width: min(600px, 96vw);
    max-height: 70vh;
  }
  
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding-bottom: 12px;
  }
  
  .modal-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
  }
  
  .close-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    font-size: 20px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    transition: all 0.2s;
  }
  
  .close-btn:hover {
    background: rgba(255,255,255,0.1);
    color: var(--text);
  }
  
  .modal-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px 0;
  }
  
  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    border-top: 1px solid rgba(255,255,255,0.1);
    padding-top: 12px;
  }
  
  .config-summary {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    margin-bottom: 16px;
  }
  
  .config-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 14px;
  }
  
  .config-label {
    color: var(--text-secondary);
    font-weight: 500;
  }
  
  .config-value {
    color: var(--text);
    font-weight: 600;
  }
  
  .config-options {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
    background: rgba(255,255,255,0.02);
    border-radius: 8px;
  }
  
  .config-options label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--text);
    cursor: pointer;
  }
  
  .config-options input[type="checkbox"] {
    cursor: pointer;
  }

  /* Sync Progress Modal */
  .sync-progress-modal {
    width: min(700px, 96vw);
    max-height: 80vh;
  }
  
  .progress-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .progress-state {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 16px;
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
  }
  
  .state-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    width: fit-content;
    padding: 8px 12px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 14px;
  }
  
  .state-badge.in-progress {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
  }
  
  .state-badge.complete {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
  }
  
  .state-badge.error {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }
  
  .state-message {
    margin: 0;
    font-size: 13px;
    color: var(--text-secondary);
  }
  
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 16px 0;
    padding: 12px;
    background: rgba(255,255,255,0.05);
    border-radius: 6px;
  }
  
  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  
  .stat-label {
    font-size: 11px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .stat-value {
    font-size: 18px;
    font-weight: 700;
    color: #3b82f6;
  }
  
  .progress-bar-container {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 12px 0;
  }
  
  .progress-label {
    font-size: 12px;
    color: var(--text-secondary);
    font-weight: 500;
  }
  
  .progress-bar {
    width: 100%;
    height: 6px;
    background: rgba(255,255,255,0.1);
    border-radius: 3px;
    overflow: hidden;
  }
  
  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  
  .progress-timeline {
    display: flex;
    flex-direction: column;
    gap: 0;
    max-height: 350px;
    overflow-y: auto;
  }
  
  .timeline-item {
    display: flex;
    gap: 12px;
    padding: 10px 12px;
    border-left: 2px solid rgba(255,255,255,0.1);
    position: relative;
    transition: background 0.2s;
  }
  
  .timeline-item:hover {
    background: rgba(255,255,255,0.05);
  }
  
  .timeline-marker {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: rgba(255,255,255,0.3);
    margin-top: 0px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    color: white;
  }
  
  .event-sync_started .timeline-marker,
  .event-track_started .timeline-marker {
    background: #3b82f6;
    color: white;
  }
  
  .event-track_synced .timeline-marker {
    background: #22c55e;
    color: white;
  }
  
  .event-track_failed .timeline-marker {
    background: #ef4444;
    color: white;
  }
  
  .event-sync_complete .timeline-marker {
    background: #22c55e;
    color: white;
  }
  
  .event-sync_error .timeline-marker {
    background: #ef4444;
    color: white;
  }
  
  .timeline-content {
    flex: 1;
    min-width: 0;
  }
  
  .timeline-type {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    text-transform: capitalize;
  }
  
  .timeline-detail {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .timeline-error {
    font-size: 12px;
    color: #ef4444;
    margin-top: 2px;
  }

  /* Scheduled Syncs */
  .scheduled-syncs-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 20px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }

  .section-header h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
  }

  .syncs-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    overflow: hidden;
  }

  .syncs-table .table-header {
    display: grid;
    grid-template-columns: 150px 150px 150px 120px 100px;
    gap: 0;
    background: rgba(255,255,255,0.05);
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .syncs-table .table-row {
    display: grid;
    grid-template-columns: 150px 150px 150px 120px 100px;
    gap: 0;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    font-size: 14px;
    color: var(--text);
  }

  .syncs-table .table-row:last-child {
    border-bottom: none;
  }

  .syncs-table .table-row:hover {
    background: rgba(255,255,255,0.02);
  }

  .col-source, .col-target, .col-interval, .col-playlists, .col-actions {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-secondary);
    font-size: 14px;
  }

  /* Schedule Modal */
  .schedule-modal {
    width: min(500px, 96vw);
    max-height: 80vh;
  }

  .schedule-modal .modal-body {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .info-text {
    font-size: 12px;
    color: var(--text-secondary);
    margin: 0;
    padding: 12px;
    background: rgba(59, 130, 246, 0.1);
    border-radius: 6px;
  }

  .btn--small {
    padding: 4px 12px;
    font-size: 12px;
  }
</style>
