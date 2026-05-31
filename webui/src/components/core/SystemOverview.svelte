<svelte:options customElement="echosync-system-overview" />
<script>
  import { onMount, onDestroy } from 'svelte';

  /**
   * @type {string} apiBase - Included for future-proofing as a Web Component.
   */
  export let apiBase = "";

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
    // Normalize apiBase
    apiBase = apiBase ? apiBase.replace(/\/$/, "") : "";
    
    await loadAll();
    loading = false;
    pollTimer = setInterval(loadAll, 10000); // Faster polling for dashboard
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
      const resp = await fetch(`${apiBase}/api/status`);
      if (resp.ok) systemStatus = await resp.json();
    } catch (e) { /* ignore */ }
  }

  async function loadJobsSummary() {
    try {
      const resp = await fetch(`${apiBase}/api/jobs/summary`);
      if (resp.ok) jobsSummary = await resp.json();
    } catch (e) { /* ignore */ }
  }

  async function loadLibraryStats() {
    try {
      const resp = await fetch(`${apiBase}/api/library/`);
      if (resp.ok) libraryStats = await resp.json();
    } catch (e) { /* ignore */ }
  }

  async function loadUpdateStatus() {
    try {
      const resp = await fetch(`${apiBase}/api/library/update-status`);
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
      const resp = await fetch(`${apiBase}/api/library/update-database?mode=${updateMode}`, {
        method: 'POST'
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
      await fetch(`${apiBase}/api/library/update-cancel`, {
        method: 'POST'
      });
      updatingDb = false;
      await loadUpdateStatus();
    } catch (e) { /* ignore */ }
  }

  function formatNumber(n) {
    if (n == null) return '0';
    return n.toLocaleString();
  }
</script>

<section class="so-container">
  {#if loading}
    <div class="so-loading">
      <div class="so-spinner"></div>
      <span>Hydrating System State...</span>
    </div>
  {:else}
    <!-- Header -->
    <header class="so-header">
      <div class="so-title-group">
        <h2 class="so-title">Overview</h2>
        <p class="so-subtitle">Real-time database and service health</p>
      </div>
      <div class="so-status-badge" class:online={systemStatus?.status === 'online'}>
        <div class="status-dot"></div>
        {systemStatus?.status === 'online' ? 'All Systems Nominal' : 'System degraded'}
      </div>
    </header>

    <!-- Stats Grid -->
    <div class="so-stats-grid">
      <div class="so-card stat-card">
        <div class="stat-icon tracks">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{formatNumber(libraryStats?.total_tracks ?? libraryStats?.tracks ?? 0)}</div>
          <div class="stat-label">Tracks</div>
        </div>
      </div>

      <div class="so-card stat-card">
        <div class="stat-icon albums">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line></svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{formatNumber(libraryStats?.total_albums ?? libraryStats?.albums ?? 0)}</div>
          <div class="stat-label">Albums</div>
        </div>
      </div>

      <div class="so-card stat-card">
        <div class="stat-icon artists">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{formatNumber(libraryStats?.total_artists ?? libraryStats?.artists ?? 0)}</div>
          <div class="stat-label">Artists</div>
        </div>
      </div>
    </div>

    <!-- Main Content Row -->
    <div class="so-content-row">
      <!-- Database Operations -->
      <div class="so-card main-card">
        <div class="card-header">
          <h3 class="card-title">Database Lifecycle</h3>
          {#if updatingDb}
             <span class="pulse-label">Scanning...</span>
          {/if}
        </div>

        {#if updatingDb}
          <div class="update-progress-container">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill animated"></div>
            </div>
            <div class="progress-details">
              <div class="detail-item">
                <span class="detail-label">Tracks</span>
                <span class="detail-value">{updateStatus?.progress?.tracks ?? 0}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Albums</span>
                <span class="detail-value">{updateStatus?.progress?.albums ?? 0}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Artists</span>
                <span class="detail-value">{updateStatus?.progress?.artists ?? 0}</span>
              </div>
            </div>
            <button class="btn-cancel" on:click={cancelUpdate}>Abort Sync</button>
          </div>
        {:else}
          <div class="update-controls">
            <button class="btn-primary-large" on:click={triggerUpdate}>
              Database Sync
            </button>
          </div>
        {/if}

        {#if error}
          <div class="error-banner">{error}</div>
        {/if}
      </div>
    </div>
  {/if}
</section>

<style>
  .so-container {
    padding: 32px;
    font-family: 'Inter', sans-serif;
    color: var(--text-primary);
  }

  /* ── Loading ──────────────────────────────────────────────────────── */
  .so-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 20px;
    padding: 80px 0;
    color: var(--text-muted);
  }

  .so-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(20, 184, 166, 0.1);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s cubic-bezier(0.5, 0, 0.5, 1) infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Header ──────────────────────────────────────────────────────── */
  .so-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 40px;
  }

  .so-title {
    margin: 0;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .so-subtitle {
    margin: 6px 0 0 0;
    font-size: 15px;
    color: var(--text-secondary);
    opacity: 0.8;
  }

  .so-status-badge {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 20px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
    color: #ef4444;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.1);
  }

  .so-status-badge.online {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.2);
    color: #10b981;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.1);
  }

  .status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 10px currentColor;
  }

  .online .status-dot {
    animation: pulse 2s infinite cubic-bezier(0.4, 0, 0.6, 1);
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.7); }
  }

  /* ── Stats Grid ──────────────────────────────────────────────────── */
  .so-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 24px;
    margin-bottom: 40px;
  }

  .so-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    border-radius: 20px;
    padding: 24px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  }

  .stat-card {
    display: flex;
    align-items: center;
    gap: 20px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .stat-card:hover {
    transform: translateY(-4px);
    border-color: rgba(20, 184, 166, 0.3);
    background: rgba(255, 255, 255, 0.03);
  }

  .stat-icon {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.04);
    color: var(--text-secondary);
    transition: transform 0.3s ease;
  }

  .stat-card:hover .stat-icon {
    transform: scale(1.1) rotate(-5deg);
  }

  .stat-icon.tracks { color: #8b5cf6; background: rgba(139, 92, 246, 0.1); }
  .stat-icon.albums { color: #ec4899; background: rgba(236, 72, 153, 0.1); }
  .stat-icon.artists { color: #3b82f6; background: rgba(59, 130, 246, 0.1); }
  .stat-icon.jobs { color: #10b981; background: rgba(16, 185, 129, 0.1); }

  .stat-value {
    font-size: 24px;
    font-weight: 800;
    line-height: 1;
    color: #fff;
    letter-spacing: -0.02em;
  }

  .stat-label {
    font-size: 12px;
    font-weight: 700;
    color: var(--text-muted);
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  /* ── Content Layout ──────────────────────────────────────────────── */
  .so-content-row {
    display: grid;
    grid-template-columns: 1fr;
    gap: 24px;
  }

  @media (max-width: 1024px) {
    .so-content-row { grid-template-columns: 1fr; }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  .card-title {
    margin: 0;
    font-size: 14px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    opacity: 0.9;
  }

  .pulse-label {
    font-size: 11px;
    font-weight: 800;
    color: var(--color-primary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    animation: blink 1.5s infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.95); }
  }

  /* ── Database Ops ────────────────────────────────────────────────── */
  .update-controls {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .mode-toggle {
    display: flex;
    background: rgba(0,0,0,0.3);
    padding: 6px;
    border-radius: 14px;
    width: fit-content;
    border: 1px solid var(--border-subtle);
  }

  .mode-btn {
    padding: 10px 20px;
    border: none;
    background: none;
    color: var(--text-muted);
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    border-radius: 10px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .mode-btn.active {
    background: var(--color-primary);
    color: #000;
    box-shadow: 0 4px 12px rgba(20, 184, 166, 0.3);
  }

  .control-help {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0;
    line-height: 1.6;
    opacity: 0.8;
  }

  .btn-primary-large {
    width: 100%;
    padding: 18px;
    background: var(--color-primary);
    color: #000;
    border: none;
    border-radius: 16px;
    font-weight: 800;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 6px 16px rgba(20, 184, 166, 0.2);
  }

  .btn-primary-large:hover:not(:disabled) {
    filter: brightness(1.1);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(20, 184, 166, 0.3);
  }

  .btn-primary-large:active:not(:disabled) {
    transform: translateY(0);
  }

  /* ── Progress ────────────────────────────────────────────────────── */
  .update-progress-container {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .progress-bar-bg {
    height: 14px;
    background: rgba(255, 255, 255, 0.04);
    border-radius: 7px;
    overflow: hidden;
    border: 1px solid var(--border-subtle);
  }

  .progress-bar-fill {
    height: 100%;
    width: 100%;
    background: linear-gradient(90deg, var(--color-primary), #3b82f6, #8b5cf6);
    background-size: 200% 100%;
  }

  .progress-bar-fill.animated {
    width: 100%;
    animation: shimmer 2s infinite linear;
  }

  @keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
  }

  .progress-details {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }

  .detail-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: rgba(255, 255, 255, 0.02);
    padding: 16px;
    border-radius: 16px;
    border: 1px solid var(--border-subtle);
    transition: background 0.2s;
  }

  .detail-item:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  .detail-label {
    font-size: 11px;
    font-weight: 800;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .detail-value {
    font-size: 22px;
    font-weight: 800;
    margin-top: 6px;
    color: #fff;
  }

  .btn-cancel {
    padding: 14px;
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-cancel:hover {
    background: #ef4444;
    color: #fff;
    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
  }

  /* ── Info List ───────────────────────────────────────────────────── */
  .info-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .info-list li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  }

  .info-list li:last-child {
    border-bottom: none;
  }

  .info-label {
    font-size: 13px;
    color: var(--text-muted);
    font-weight: 600;
  }

  .info-value {
    font-size: 14px;
    font-weight: 700;
    color: #fff;
  }

  .info-value.warn {
    color: #f59e0b;
    text-shadow: 0 0 8px rgba(245, 158, 11, 0.3);
  }

  .error-banner {
    margin-top: 20px;
    padding: 14px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 12px;
    color: #ef4444;
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .error-banner::before {
    content: '⚠️';
  }
</style>

