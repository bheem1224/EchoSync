<svelte:options customElement={{
  tag: 'echosync-system-overview',
  shadow: 'none'
}} />
<script>
  import { onMount, onDestroy } from 'svelte';

  let systemStatus = null;
  let jobsSummary = null;
  let libraryStats = null;
  let updateStatus = null;
  let loading = true;
  let updatingDb = false;
  let updateMode = 'incremental';
  let error = null;
  let pollTimer = null;

  onMount(async () => {
    await loadAll();
    loading = false;
    pollTimer = setInterval(loadAll, 15000);
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
  });

  async function loadAll() {
    await Promise.allSettled([
      loadSystemStatus(),
      loadJobsSummary(),
      loadLibraryStats(),
      loadUpdateStatus()
    ]);
  }

  async function loadSystemStatus() {
    try {
      const resp = await fetch('/api/system/status', { credentials: 'include' });
      if (resp.ok) systemStatus = await resp.json();
    } catch (e) { /* ignore */ }
  }

  async function loadJobsSummary() {
    try {
      const resp = await fetch('/api/jobs/summary', { credentials: 'include' });
      if (resp.ok) jobsSummary = await resp.json();
    } catch (e) { /* ignore */ }
  }

  async function loadLibraryStats() {
    try {
      const resp = await fetch('/api/library/', { credentials: 'include' });
      if (resp.ok) libraryStats = await resp.json();
    } catch (e) { /* ignore */ }
  }

  async function loadUpdateStatus() {
    try {
      const resp = await fetch('/api/library/update-status', { credentials: 'include' });
      if (resp.ok) {
        updateStatus = await resp.json();
        updatingDb = updateStatus?.running || false;
      }
    } catch (e) { /* ignore */ }
  }

  async function triggerUpdate() {
    if (updatingDb) return;
    updatingDb = true;
    error = null;
    try {
      const resp = await fetch(`/api/library/update-database?mode=${updateMode}`, {
        method: 'POST',
        credentials: 'include'
      });
      const data = await resp.json();
      if (!resp.ok) {
        error = data.error || 'Failed to start update';
        updatingDb = false;
      }
    } catch (e) {
      error = e.message;
      updatingDb = false;
    }
  }

  async function cancelUpdate() {
    try {
      await fetch('/api/library/update-cancel', {
        method: 'POST',
        credentials: 'include'
      });
      updatingDb = false;
      await loadUpdateStatus();
    } catch (e) { /* ignore */ }
  }

  function formatNumber(n) {
    if (n == null) return '—';
    return n.toLocaleString();
  }

  function formatUptime(ts) {
    if (!ts) return 'Unknown';
    return ts;
  }
</script>

<section class="so-root">
  {#if loading}
    <div class="so-loading">
      <div class="so-spinner"></div>
      <span>Loading system overview…</span>
    </div>
  {:else}
    <!-- System State Row -->
    <div class="so-header">
      <h2 class="so-title">System Overview</h2>
      <div class="so-status-pill" class:so-online={systemStatus?.status === 'online'}>
        <span class="so-pulse"></span>
        {systemStatus?.status === 'online' ? 'All Systems Nominal' : 'Offline'}
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="so-grid">
      <!-- Library Stats Card -->
      <div class="so-stat-card">
        <div class="so-stat-icon">🎵</div>
        <div class="so-stat-body">
          <span class="so-stat-value">{formatNumber(libraryStats?.total_tracks ?? libraryStats?.tracks ?? 0)}</span>
          <span class="so-stat-label">Tracks</span>
        </div>
      </div>

      <div class="so-stat-card">
        <div class="so-stat-icon">💿</div>
        <div class="so-stat-body">
          <span class="so-stat-value">{formatNumber(libraryStats?.total_albums ?? libraryStats?.albums ?? 0)}</span>
          <span class="so-stat-label">Albums</span>
        </div>
      </div>

      <div class="so-stat-card">
        <div class="so-stat-icon">🎤</div>
        <div class="so-stat-body">
          <span class="so-stat-value">{formatNumber(libraryStats?.total_artists ?? libraryStats?.artists ?? 0)}</span>
          <span class="so-stat-label">Artists</span>
        </div>
      </div>

      <div class="so-stat-card">
        <div class="so-stat-icon">⚙️</div>
        <div class="so-stat-body">
          <span class="so-stat-value">{jobsSummary?.running_jobs ?? 0}</span>
          <span class="so-stat-label">Active Jobs</span>
        </div>
      </div>
    </div>

    <!-- Jobs Summary -->
    <div class="so-section">
      <h3 class="so-section-title">Job Queue Status</h3>
      <div class="so-jobs-row">
        <div class="so-jobs-metric">
          <span class="so-metric-dot so-dot-green"></span>
          <span>{jobsSummary?.running_jobs ?? 0} Running</span>
        </div>
        <div class="so-jobs-metric">
          <span class="so-metric-dot so-dot-blue"></span>
          <span>{jobsSummary?.queued_jobs ?? 0} Queued</span>
        </div>
        {#if jobsSummary?.errors?.length}
          <div class="so-jobs-metric so-jobs-error">
            <span class="so-metric-dot so-dot-red"></span>
            <span>{jobsSummary.errors.length} Error{jobsSummary.errors.length > 1 ? 's' : ''}</span>
          </div>
        {/if}
        {#if jobsSummary?.last_run}
          <div class="so-jobs-metric so-jobs-last">
            Last run: {new Date(jobsSummary.last_run * 1000).toLocaleTimeString()}
          </div>
        {/if}
      </div>
    </div>

    <!-- System Info -->
    <div class="so-section">
      <h3 class="so-section-title">Environment</h3>
      <div class="so-info-grid">
        <div class="so-info-item">
          <span class="so-info-key">Platform</span>
          <span class="so-info-val">{systemStatus?.platform ?? '—'}</span>
        </div>
        <div class="so-info-item">
          <span class="so-info-key">Python</span>
          <span class="so-info-val">{systemStatus?.python_version ?? '—'}</span>
        </div>
        <div class="so-info-item">
          <span class="so-info-key">Restart Pending</span>
          <span class="so-info-val" class:so-warn={systemStatus?.restart_pending}>
            {systemStatus?.restart_pending ? 'Yes' : 'No'}
          </span>
        </div>
      </div>
    </div>

    <!-- Database Update Action -->
    <div class="so-section so-update-section">
      <h3 class="so-section-title">Database Update</h3>
      
      {#if updatingDb}
        <div class="so-update-progress">
          <div class="so-progress-bar">
            <div class="so-progress-fill"></div>
          </div>
          <div class="so-progress-stats">
            <span>Artists: {updateStatus?.progress?.artists ?? 0}</span>
            <span>Albums: {updateStatus?.progress?.albums ?? 0}</span>
            <span>Tracks: {updateStatus?.progress?.tracks ?? 0}</span>
          </div>
          <button class="so-btn so-btn-danger" on:click={cancelUpdate}>Cancel Update</button>
        </div>
      {:else}
        <div class="so-update-controls">
          <div class="so-mode-selector">
            <button
              class="so-mode-btn"
              class:so-mode-active={updateMode === 'incremental'}
              on:click={() => updateMode = 'incremental'}
            >Incremental</button>
            <button
              class="so-mode-btn"
              class:so-mode-active={updateMode === 'full'}
              on:click={() => updateMode = 'full'}
            >Full Refresh</button>
          </div>
          <button class="so-btn so-btn-primary" on:click={triggerUpdate}>
            Run Database Update
          </button>
        </div>
      {/if}

      {#if error}
        <div class="so-error">{error}</div>
      {/if}

      {#if updateStatus?.progress}
        <div class="so-last-update-stats">
          <span>Last run: {updateStatus.progress.successful ?? 0} synced, {updateStatus.progress.failed ?? 0} failed</span>
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .so-root {
    padding: 24px;
    color: var(--text-primary, #e2e8f0);
  }

  .so-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 48px 0;
    color: var(--text-muted, rgba(255,255,255,0.4));
    font-size: 14px;
  }

  .so-spinner {
    width: 24px; height: 24px;
    border: 3px solid rgba(255,255,255,0.06);
    border-top-color: var(--color-primary, #14b8a6);
    border-radius: 50%;
    animation: so-spin 0.7s linear infinite;
  }
  @keyframes so-spin { to { transform: rotate(360deg); } }

  /* ── Header ──────────────────────────────────────────────────────── */
  .so-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .so-title {
    margin: 0;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.3px;
  }
  .so-status-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.05em;
    background: rgba(239, 68, 68, 0.12);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.25);
  }
  .so-status-pill.so-online {
    background: rgba(34, 197, 94, 0.12);
    color: #22c55e;
    border-color: rgba(34, 197, 94, 0.25);
  }
  .so-pulse {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: so-pulse-anim 2s ease-in-out infinite;
  }
  @keyframes so-pulse-anim {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%      { opacity: 0.5; transform: scale(0.75); }
  }

  /* ── Stats Grid ──────────────────────────────────────────────────── */
  .so-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px;
    margin-bottom: 28px;
  }
  .so-stat-card {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 18px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    transition: border-color 0.2s, transform 0.2s;
  }
  .so-stat-card:hover {
    border-color: rgba(255, 255, 255, 0.12);
    transform: translateY(-2px);
  }
  .so-stat-icon {
    font-size: 28px;
    flex-shrink: 0;
  }
  .so-stat-body {
    display: flex;
    flex-direction: column;
  }
  .so-stat-value {
    font-size: 24px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.5px;
  }
  .so-stat-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--text-muted, rgba(255,255,255,0.4));
    margin-top: 4px;
  }

  /* ── Sections ────────────────────────────────────────────────────── */
  .so-section {
    padding: 18px 0;
    border-top: 1px solid rgba(255,255,255,0.05);
  }
  .so-section-title {
    margin: 0 0 14px 0;
    font-size: 11px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: rgba(255,255,255,0.4);
  }

  /* ── Jobs row ────────────────────────────────────────────────────── */
  .so-jobs-row {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }
  .so-jobs-metric {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 600;
  }
  .so-metric-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .so-dot-green { background: #22c55e; }
  .so-dot-blue  { background: #3b82f6; }
  .so-dot-red   { background: #ef4444; }
  .so-jobs-error { color: #ef4444; }
  .so-jobs-last  { color: var(--text-muted, rgba(255,255,255,0.4)); font-size: 11px; margin-left: auto; }

  /* ── Info Grid ───────────────────────────────────────────────────── */
  .so-info-grid {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
  }
  .so-info-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .so-info-key {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted, rgba(255,255,255,0.4));
  }
  .so-info-val {
    font-size: 14px;
    font-weight: 600;
  }
  .so-info-val.so-warn {
    color: #eab308;
  }

  /* ── Database Update ─────────────────────────────────────────────── */
  .so-update-section {
    border-top: 1px solid rgba(255,255,255,0.05);
  }
  .so-update-controls {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
  }
  .so-mode-selector {
    display: flex;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    overflow: hidden;
  }
  .so-mode-btn {
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
    background: none;
    border: none;
    color: var(--text-muted, rgba(255,255,255,0.4));
    cursor: pointer;
    transition: all 0.2s;
  }
  .so-mode-btn.so-mode-active {
    background: var(--color-primary, #14b8a6);
    color: #000;
  }
  .so-btn {
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 13px;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
  }
  .so-btn-primary {
    background: var(--color-primary, #14b8a6);
    color: #000;
  }
  .so-btn-primary:hover {
    filter: brightness(1.1);
    transform: translateY(-1px);
  }
  .so-btn-danger {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }
  .so-btn-danger:hover {
    background: rgba(239, 68, 68, 0.25);
  }

  /* ── Progress ────────────────────────────────────────────────────── */
  .so-update-progress {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .so-progress-bar {
    width: 100%;
    height: 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 3px;
    overflow: hidden;
  }
  .so-progress-fill {
    height: 100%;
    width: 40%;
    background: linear-gradient(90deg, var(--color-primary, #14b8a6), #3b82f6);
    border-radius: 3px;
    animation: so-progress-pulse 1.5s ease-in-out infinite;
  }
  @keyframes so-progress-pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.6; }
  }
  .so-progress-stats {
    display: flex;
    gap: 16px;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted, rgba(255,255,255,0.5));
  }

  .so-error {
    margin-top: 10px;
    padding: 10px 14px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 8px;
    color: #ef4444;
    font-size: 13px;
  }

  .so-last-update-stats {
    margin-top: 8px;
    font-size: 11px;
    color: var(--text-muted, rgba(255,255,255,0.35));
  }
</style>
