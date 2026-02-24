<script>
  import { onMount, onDestroy } from 'svelte';
  import apiClient from '../../api/client';
  import { health } from '../../stores/health';
  import { feedback } from '../../stores/feedback';

  let healthPollHandle = null;
  let updateMode = 'incremental';
  let isUpdating = false;
  let updateProgress = 0;
  let updateStatus = '';
  let scanningStatus = false;
  
  // Database stats
  let dbStats = {
    artists: 0,
    albums: 0,
    tracks: 0,
    size: '0 MB',
    lastRefresh: null,
    completed: 0,
    total: 0,
    failed: 0
  };

  onMount(async () => {
    await health.load();
    healthPollHandle = health.poll(30000);
    await loadDatabaseStats();

    // Only poll update-status if an update is in progress.  This avoids
    // perpetual polling when nothing is running, which was causing
    // excessive requests and database locks.
    try {
      const resp = await apiClient.get('/library/update-status');
      if (resp.data?.running) {
        startProgressPolling();
      }
    } catch (err) {
      // ignore; we'll start polling when the user triggers an update
      console.debug('Initial update-status check failed, will not poll until update requested');
    }
  });

  onDestroy(() => {
    health.stop();
  });

  async function loadDatabaseStats(retry = true) {
    try {
      const response = await apiClient.get('/library');
      if (response.data) {
        // Get stats from the API response
        const stats = response.data.stats || {};
        
        // Use synced_tracks/artists/albums (what's actually in SoulSync database)
        dbStats.tracks = stats.synced_tracks || 0;
        dbStats.artists = stats.synced_artists || 0;
        dbStats.albums = stats.synced_albums || 0;
        
        // Use actual database size from API (in MB)
        const dbSizeMB = stats.database_size_mb || 0;
        dbStats.size = dbSizeMB > 0 ? `${dbSizeMB} MB` : '0 MB';
        
        // Get last refresh from config or use current time as placeholder
        dbStats.lastRefresh = new Date().toISOString();
      }
    } catch (error) {
      console.error('Failed to load database stats:', error);
      // if we failed due to a transient lock, try again once
      if (retry) {
        setTimeout(() => loadDatabaseStats(false), 5000);
      }
    }
  }

  let pollingIntervalId = null;

  async function startProgressPolling() {
    // Avoid starting multiple intervals
    if (pollingIntervalId) return;

    pollingIntervalId = setInterval(async () => {
      try {
        const response = await apiClient.get('/library/update-status');
        if (response.data) {
          const isRunning = response.data.running || false;
          const progress = response.data.progress || {};
          
          if (isRunning) {
            isUpdating = true;
            scanningStatus = true;
            
            // Calculate progress percentage based on tracks processed
            const total = (progress.total ?? dbStats.tracks) || 1000;
            const processed = progress.tracks || 0;
            updateProgress = Math.min(100, Math.round((processed / total) * 100));
            
            updateStatus = `Processing: ${progress.artists || 0} artists, ${progress.albums || 0} albums, ${progress.tracks || 0} tracks`;
          } else if (isUpdating) {
            // Just finished
            isUpdating = false;
            scanningStatus = false;
            updateProgress = 100;
            updateStatus = 'Complete';
            await loadDatabaseStats();

            // Stop polling since update is finished
            if (pollingIntervalId) {
              clearInterval(pollingIntervalId);
              pollingIntervalId = null;
            }

            setTimeout(() => {
              updateProgress = 0;
              updateStatus = '';
            }, 3000);
          } else {
             // Not running and not updating, stop polling
             if (pollingIntervalId) {
                 clearInterval(pollingIntervalId);
                 pollingIntervalId = null;
             }
          }
        }
      } catch (error) {
        // Silently fail - polling
      }
    }, 2000);
  }

  onDestroy(() => {
    if (pollingIntervalId) clearInterval(pollingIntervalId);
    health.stop();
  });

  async function updateDatabase() {
    if (isUpdating) return;

    try {
      isUpdating = true;
      updateProgress = 0;
      updateStatus = 'Starting update...';
      
      // Start polling for progress
      startProgressPolling();

      const params = `?mode=${updateMode}`;
      await apiClient.post(`/library/update-database${params}`);
      
      feedback.addToast(`Database update started (${updateMode})`, 'success');
    } catch (error) {
      console.error('Failed to start database update:', error);
      feedback.addToast('Failed to start database update', 'error');
      isUpdating = false;
      updateProgress = 0;
      updateStatus = '';
    }
  }

  $: systemStatus = $health.status;
  $: serviceHealth = $health.services || {};
  // prefer summary fields when available (handles startup/empty results)
  $: healthyServices = $health.summary?.operational ?? Object.values(serviceHealth).filter(s => s.status === 'healthy').length;
  $: totalServices = $health.summary?.total ?? Object.keys(serviceHealth).length;
</script>

<svelte:head>
  <title>Dashboard • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div>
      <h1>Dashboard</h1>
      <p class="subtitle">System overview and database management</p>
    </div>
  </header>

  <div class="dashboard-grid">
    <!-- System Status Card -->
    <div class="card system-status">
      <div class="card-header">
        <h2>System Status</h2>
      </div>
      
      <div class="status-display">
        <div class="status-circle {systemStatus}">
          <div class="pulse"></div>
          <div class="core"></div>
        </div>
        <div class="status-info">
          <div class="status-label">Status</div>
          <div class="status-value {systemStatus}">{systemStatus || 'Unknown'}</div>
          <div class="status-subtitle">
            {healthyServices}/{totalServices} services operational
          </div>
        </div>
      </div>

      <div class="services-list">
        {#each Object.entries(serviceHealth) as [id, data]}
          <div class="service-item">
            <span class="service-dot {data.status}"></span>
            <span class="service-name">{id}</span>
            <span class="service-status {data.status}">{data.status}</span>
          </div>
        {/each}
      </div>
    </div>

    <!-- Database Updater Card -->
    <div class="card database-updater">
      <div class="card-header">
        <h2>Database Updater</h2>
        <button class="help-btn" title="Update your music library database">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 16v-4M12 8h.01"></path>
          </svg>
        </button>
      </div>

      {#if dbStats.lastRefresh}
        <div class="last-refresh">
          Last Full Refresh: {new Date(dbStats.lastRefresh).toLocaleString('en-US', { 
            month: 'numeric', 
            day: 'numeric', 
            year: 'numeric', 
            hour: 'numeric', 
            minute: '2-digit', 
            hour12: true 
          })}
        </div>
      {/if}

      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-label">Artists:</div>
          <div class="stat-value">{dbStats.artists.toLocaleString()}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Albums:</div>
          <div class="stat-value">{dbStats.albums.toLocaleString()}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Tracks:</div>
          <div class="stat-value">{dbStats.tracks.toLocaleString()}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">Size:</div>
          <div class="stat-value">{dbStats.size}</div>
        </div>
      </div>

      <div class="update-controls">
        <select bind:value={updateMode} disabled={isUpdating} class="mode-select">
          <option value="incremental">Incremental Update</option>
          <option value="full">Full Refresh</option>
        </select>

        <button 
          class="btn-update" 
          on:click={updateDatabase}
          disabled={isUpdating}
        >
          {isUpdating ? 'Updating...' : 'Update Database'}
        </button>
      </div>

      {#if isUpdating || updateStatus}
        <div class="update-progress">
          <div class="progress-info">
            <span class="progress-label">{updateStatus}</span>
            {#if dbStats.total > 0}
              <span class="progress-count">{dbStats.completed}/{dbStats.total} items (0.0%)</span>
            {/if}
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width: {updateProgress}%"></div>
          </div>
          {#if dbStats.completed > 0}
            <div class="completion-status">
              Completed: {dbStats.completed} successful, {dbStats.failed} failed.
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 24px;
    padding: 24px;
  }

  .page__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .page__header h1 {
    margin: 0 0 8px 0;
    font-size: 32px;
    font-weight: 700;
    color: var(--text);
  }

  .subtitle {
    margin: 0;
    color: var(--muted);
    font-size: 15px;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: 400px 1fr;
    gap: 24px;
  }

  @media (max-width: 1200px) {
    .dashboard-grid {
      grid-template-columns: 1fr;
    }
  }

  .card {
    background: var(--card-bg, rgba(255, 255, 255, 0.03));
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
    border-radius: 16px;
    padding: 24px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  .card-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
  }

  .help-btn {
    background: none;
    border: none;
    color: var(--muted);
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    transition: color 0.2s;
  }

  .help-btn:hover {
    color: var(--text);
  }

  /* System Status Styles */
  .status-display {
    display: flex;
    align-items: center;
    gap: 24px;
    margin-bottom: 32px;
  }

  .status-circle {
    position: relative;
    width: 120px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .pulse {
    position: absolute;
    width: 100%;
    height: 100%;
    border-radius: 50%;
    background: radial-gradient(circle, transparent 60%, currentColor 100%);
    opacity: 0.3;
    animation: pulse 2s ease-in-out infinite;
  }

  .core {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 30px currentColor;
  }

  .status-circle.healthy { color: #00e676; }
  .status-circle.degraded { color: #ff9800; }
  .status-circle.unhealthy { color: #ef4444; }
  .status-circle.unknown { color: #6b7280; }

  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 0.3; }
    50% { transform: scale(1.1); opacity: 0.1; }
  }

  .status-info {
    flex: 1;
  }

  .status-label {
    font-size: 13px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
  }

  .status-value {
    font-size: 32px;
    font-weight: 700;
    text-transform: capitalize;
    margin-bottom: 8px;
  }

  .status-value.healthy { color: #00e676; }
  .status-value.degraded { color: #ff9800; }
  .status-value.unhealthy { color: #ef4444; }
  .status-value.unknown { color: #6b7280; }

  .status-subtitle {
    font-size: 14px;
    color: var(--muted);
  }

  .services-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .service-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
  }

  .service-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .service-dot.healthy { background: #00e676; box-shadow: 0 0 8px #00e676; }
  .service-dot.degraded { background: #ff9800; box-shadow: 0 0 8px #ff9800; }
  .service-dot.unhealthy { background: #ef4444; box-shadow: 0 0 8px #ef4444; }

  .service-name {
    flex: 1;
    font-size: 14px;
    color: var(--text);
    text-transform: capitalize;
  }

  .service-status {
    font-size: 11px;
    text-transform: uppercase;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 4px;
  }

  .service-status.healthy { 
    background: rgba(0, 230, 118, 0.15); 
    color: #00e676; 
  }
  .service-status.degraded { 
    background: rgba(255, 152, 0, 0.15); 
    color: #ff9800; 
  }
  .service-status.unhealthy { 
    background: rgba(239, 68, 68, 0.15); 
    color: #ef4444; 
  }

  /* Database Updater Styles */
  .last-refresh {
    font-size: 13px;
    color: var(--muted);
    margin-bottom: 20px;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 6px;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }

  .stat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
  }

  .stat-label {
    font-size: 14px;
    color: var(--muted);
  }

  .stat-value {
    font-size: 18px;
    font-weight: 700;
    color: var(--text);
  }

  .update-controls {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
  }

  .mode-select {
    flex: 1;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
    border-radius: 8px;
    color: var(--text);
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23ffffff' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 36px;
  }

  .mode-select:hover:not(:disabled) {
    background-color: rgba(255, 255, 255, 0.08);
    background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23ffffff' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  }

  .mode-select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .mode-select option {
    background: #1a1a1a;
    color: var(--text);
    padding: 12px;
  }

  .btn-update {
    padding: 12px 24px;
    background: #00e676;
    color: #000;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .btn-update:hover:not(:disabled) {
    background: #00ff88;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 230, 118, 0.3);
  }

  .btn-update:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .update-progress {
    padding: 16px;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
  }

  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .progress-label {
    font-size: 14px;
    color: var(--text);
    font-weight: 500;
  }

  .progress-count {
    font-size: 12px;
    color: var(--muted);
  }

  .progress-bar {
    width: 100%;
    height: 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 12px;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #00e676, #00ff88);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .completion-status {
    font-size: 13px;
    color: var(--muted);
  }
</style>
