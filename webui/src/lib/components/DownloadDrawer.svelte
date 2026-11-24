<script>
  import { onMount, onDestroy } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import { isDownloadDrawerOpen, closeDownloadDrawer } from '../../stores/ui';
  import {
    downloadQueue,
    activeDownloads,
    downloadHistory,
    downloadStats,
    fetchDownloads
  } from '../../stores/downloads';
  import apiClient from '../../api/client';
  import { feedback } from '../../stores/feedback';

  let activeTab = 'active'; // 'active' | 'failed' | 'completed'
  let searchQuery = '';
  let isActionPending = false;
  let pollIntervalId = null;

  // Quality Profiles
  let qualityProfiles = [];
  let selectedProfileId = '';

  // Partition history into Completed vs Failed/Cancelled for clean scannability
  $: completedDownloads = $downloadHistory.filter(
    (i) => String(i.status || '').toUpperCase() === 'COMPLETED'
  );
  $: failedDownloads = $downloadHistory.filter(
    (i) => String(i.status || '').toUpperCase() !== 'COMPLETED'
  );

  // Filtered list for active tab
  $: normalizedQuery = searchQuery.trim().toLowerCase();
  $: currentRawItems =
    activeTab === 'active'
      ? $activeDownloads
      : activeTab === 'failed'
        ? failedDownloads
        : completedDownloads;
  $: visibleItems = normalizedQuery
    ? currentRawItems.filter((item) => {
        const haystack = [
          item.artist,
          item.title,
          item.raw_title,
          item.album,
          item.error_reason,
          item.cancellation_reason
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return haystack.includes(normalizedQuery);
      })
    : currentRawItems;

  function formatSpeed(bytesPerSec) {
    if (!bytesPerSec || isNaN(bytesPerSec) || bytesPerSec <= 0) return '0 KB/s';
    const kb = bytesPerSec / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB/s`;
    const mb = kb / 1024;
    return `${mb.toFixed(2)} MB/s`;
  }

  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  function statusLabel(status) {
    const s = String(status || '').toUpperCase();
    switch (s) {
      case 'DOWNLOADING':
        return 'Downloading';
      case 'SEARCHING':
        return 'Searching';
      case 'VERIFYING':
        return 'Verifying';
      case 'RETRYING':
        return 'Retrying';
      case 'PAUSED':
        return 'Paused';
      case 'QUEUED':
        return 'Queued';
      case 'COMPLETED':
        return 'Completed';
      case 'NOT_FOUND':
        return 'Not Found';
      case 'CANCELLED':
        return 'Cancelled';
      case 'FAILED':
        return 'Failed';
      default:
        return s ? s.charAt(0) + s.slice(1).toLowerCase() : 'Queued';
    }
  }

  function statusTone(status) {
    const s = String(status || '').toUpperCase();
    if (s === 'DOWNLOADING' || s === 'VERIFYING') return 'primary';
    if (s === 'COMPLETED') return 'success';
    if (s === 'SEARCHING' || s === 'RETRYING' || s === 'PAUSED') return 'warning';
    if (s === 'FAILED' || s === 'NOT_FOUND') return 'danger';
    return 'muted';
  }

  async function loadQualityProfiles() {
    try {
      const resp = await apiClient
        .get('/system/config/quality-profiles')
        .catch(() => apiClient.get('/system/quality-profiles'));
      const profiles = resp.data?.profiles || [];
      qualityProfiles = Array.isArray(profiles) ? profiles : [];

      const saved = localStorage.getItem('echosync.active_quality_profile');
      if (saved && qualityProfiles.some((p) => String(p.id) === String(saved))) {
        selectedProfileId = saved;
      } else if (qualityProfiles.length > 0) {
        selectedProfileId = String(qualityProfiles[0].id);
      }
    } catch (err) {
      console.warn('Failed to load quality profiles in DownloadDrawer:', err);
    }
  }

  function handleProfileChange(e) {
    selectedProfileId = e.target.value;
    try {
      localStorage.setItem('echosync.active_quality_profile', selectedProfileId);
      const selected = qualityProfiles.find((p) => String(p.id) === String(selectedProfileId));
      if (selected) {
        feedback.info(`Active Quality Profile: ${selected.name || selectedProfileId}`);
      }
    } catch (err) {
      console.error(err);
    }
  }

  $: if (typeof document !== 'undefined') {
    document.body.classList.toggle('overflow-hidden', $isDownloadDrawerOpen);
  }

  $: if ($isDownloadDrawerOpen) {
    fetchDownloads();
    loadQualityProfiles();
    if (!pollIntervalId) {
      pollIntervalId = setInterval(fetchDownloads, 2000);
    }
  } else {
    if (pollIntervalId) {
      clearInterval(pollIntervalId);
      pollIntervalId = null;
    }
  }

  onMount(() => {
    fetchDownloads();
    loadQualityProfiles();
  });

  onDestroy(() => {
    if (pollIntervalId) {
      clearInterval(pollIntervalId);
      pollIntervalId = null;
    }
    if (typeof document !== 'undefined') {
      document.body.classList.remove('overflow-hidden');
    }
  });

  async function triggerRun() {
    if (isActionPending) return;
    isActionPending = true;
    try {
      await apiClient.post('/core/downloads/run');
      feedback.success('Download processing started');
      await fetchDownloads();
    } catch (err) {
      if (err.response?.status === 409) {
        feedback.warning('Download manager is already actively running');
      } else {
        feedback.error(err.response?.data?.detail || 'Failed to trigger downloads');
      }
    } finally {
      isActionPending = false;
    }
  }

  async function startNowItem(item) {
    try {
      await apiClient.post(`/core/downloads/${item.id}/start-now`);
      feedback.success(`Started "${item.title || item.raw_title || 'track'}"`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to start download: ${err.response?.data?.detail || err.message}`);
    }
  }

  async function requeueItem(item) {
    try {
      await apiClient.post(`/core/downloads/${item.id}/requeue`);
      feedback.success(`Re-queued "${item.title || item.raw_title || 'track'}"`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to re-queue download: ${err.response?.data?.detail || err.message}`);
    }
  }

  async function pauseItem(item) {
    try {
      await apiClient.post(`/core/downloads/${item.id}/pause`);
      feedback.info(`Paused "${item.title || item.raw_title || 'track'}"`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to pause download: ${err.response?.data?.detail || err.message}`);
    }
  }

  async function deleteItem(item) {
    try {
      await apiClient.delete(`/core/downloads/${item.id}`);
      feedback.success(`Removed "${item.title || item.raw_title || 'track'}"`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to remove download: ${err.response?.data?.detail || err.message}`);
    }
  }

  async function requeueAllFailed() {
    if (isActionPending) return;
    isActionPending = true;
    try {
      const res = await apiClient.post('/core/downloads/requeue-all-failed');
      const count = res.data?.count ?? '';
      feedback.success(`Re-queued all failed items (${count})`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to re-queue failed downloads: ${err.response?.data?.detail || err.message}`);
    } finally {
      isActionPending = false;
    }
  }

  async function clearFailed() {
    if (isActionPending) return;
    isActionPending = true;
    try {
      const res = await apiClient.delete('/core/downloads/failed');
      const count = res.data?.count ?? '';
      feedback.success(`Cleared failed downloads (${count})`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to clear failed downloads: ${err.response?.data?.detail || err.message}`);
    } finally {
      isActionPending = false;
    }
  }

  async function clearAll() {
    if (!confirm('Are you sure you want to clear the entire download queue and history?')) return;
    try {
      await apiClient.delete('/core/downloads/queue');
      feedback.success('Download queue cleared');
      await fetchDownloads();
    } catch (err) {
      feedback.error('Failed to clear download queue');
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Escape' && $isDownloadDrawerOpen) {
      closeDownloadDrawer();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if $isDownloadDrawerOpen}
  <!-- Backdrop -->
  <div
    class="dm-backdrop"
    on:click={closeDownloadDrawer}
    transition:fade={{ duration: 180 }}
    aria-hidden="true"
  ></div>

  <!-- Minimalist Slide-over Drawer -->
  <aside
    class="dm-drawer"
    transition:fly={{ x: 460, duration: 220 }}
    aria-label="Download Manager Drawer"
  >
    <!-- Header -->
    <header class="dm-header">
      <div class="dm-header-top">
        <div class="dm-title-group">
          <button
            type="button"
            class="dm-icon-btn dm-mobile-back"
            on:click={closeDownloadDrawer}
            aria-label="Back"
            title="Back"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" class="dm-svg">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
          </button>

          <div>
            <h2 class="dm-title">Downloads</h2>
            <p class="dm-subtitle">
              {#if $downloadStats.totalSpeed > 0}
                <span class="dm-speed-inline">{formatSpeed($downloadStats.totalSpeed)}</span>
                <span class="dm-sep">·</span>
              {/if}
              <span>{$activeDownloads.length} active</span>
              {#if failedDownloads.length > 0}
                <span class="dm-sep">·</span>
                <span class="dm-text-danger">{failedDownloads.length} failed</span>
              {/if}
              {#if completedDownloads.length > 0}
                <span class="dm-sep">·</span>
                <span class="dm-text-success">{completedDownloads.length} done</span>
              {/if}
            </p>
          </div>
        </div>

        <div class="dm-header-actions">
          <button
            type="button"
            class="dm-primary-btn"
            on:click={triggerRun}
            disabled={isActionPending}
            title="Process queued downloads now"
          >
            {#if $downloadStats.isRunning}
              <span class="dm-dot dm-dot--live"></span>
              <span>Running</span>
            {:else}
              <svg viewBox="0 0 24 24" fill="currentColor" class="dm-svg-sm">
                <path d="M8 5.14v14l11-7-11-7z" />
              </svg>
              <span>Run</span>
            {/if}
          </button>

          <button
            type="button"
            class="dm-icon-btn dm-desktop-close"
            on:click={closeDownloadDrawer}
            aria-label="Close Drawer"
            title="Close (Esc)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" class="dm-svg">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Quality Profile Selector -->
      {#if qualityProfiles && qualityProfiles.length > 0}
        <div class="dm-profile-row">
          <label class="dm-profile-label" for="dm-quality-profile">Profile</label>
          <select
            id="dm-quality-profile"
            class="dm-select"
            value={selectedProfileId}
            on:change={handleProfileChange}
          >
            {#each qualityProfiles as profile}
              <option value={String(profile.id)}>
                {profile.name} ({profile.preferred_format || 'Auto'})
              </option>
            {/each}
          </select>
        </div>
      {/if}
    </header>

    <!-- Compact Metrics Strip -->
    <div class="dm-metrics">
      <div class="dm-metric">
        <span class="dm-metric-label">Speed</span>
        <span class="dm-metric-val dm-metric-val--primary">{formatSpeed($downloadStats.totalSpeed)}</span>
      </div>
      <div class="dm-metric">
        <span class="dm-metric-label">Active</span>
        <span class="dm-metric-val">{$downloadStats.activeCount}</span>
      </div>
      <div class="dm-metric">
        <span class="dm-metric-label">Queued</span>
        <span class="dm-metric-val">{$downloadStats.queuedCount}</span>
      </div>
      <div class="dm-metric">
        <span class="dm-metric-label">Failed</span>
        <span class="dm-metric-val" class:dm-metric-val--danger={failedDownloads.length > 0}>{failedDownloads.length}</span>
      </div>
      <div class="dm-metric">
        <span class="dm-metric-label">Done</span>
        <span class="dm-metric-val" class:dm-metric-val--success={completedDownloads.length > 0}>{completedDownloads.length}</span>
      </div>
    </div>

    <!-- Navigation Tabs & Context Toolbar -->
    <div class="dm-controls">
      <div class="dm-tabs" role="tablist" aria-label="Download queue views">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'active'}
          class="dm-tab"
          class:dm-tab--active={activeTab === 'active'}
          on:click={() => { activeTab = 'active'; searchQuery = ''; }}
        >
          <span>Active</span>
          <span class="dm-tab-count">{$activeDownloads.length}</span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'failed'}
          class="dm-tab"
          class:dm-tab--active={activeTab === 'failed'}
          on:click={() => { activeTab = 'failed'; searchQuery = ''; }}
        >
          <span>Failed</span>
          <span
            class="dm-tab-count"
            class:dm-tab-count--danger={failedDownloads.length > 0}
          >
            {failedDownloads.length}
          </span>
        </button>

        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'completed'}
          class="dm-tab"
          class:dm-tab--active={activeTab === 'completed'}
          on:click={() => { activeTab = 'completed'; searchQuery = ''; }}
        >
          <span>Completed</span>
          <span
            class="dm-tab-count"
            class:dm-tab-count--success={completedDownloads.length > 0}
          >
            {completedDownloads.length}
          </span>
        </button>
      </div>

      <!-- Contextual Filter & Bulk Actions Bar -->
      {#if currentRawItems.length > 0}
        <div class="dm-toolbar">
          {#if currentRawItems.length > 4}
            <div class="dm-search-wrap">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" class="dm-search-icon">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z" />
              </svg>
              <input
                type="text"
                class="dm-search-input"
                placeholder="Filter tracks…"
                bind:value={searchQuery}
              />
            </div>
          {:else}
            <div class="dm-toolbar-spacer"></div>
          {/if}

          <div class="dm-bulk-actions">
            {#if activeTab === 'failed' && failedDownloads.length > 0}
              <button
                type="button"
                class="dm-ghost-btn"
                on:click={requeueAllFailed}
                disabled={isActionPending}
                title="Re-queue all failed items"
              >
                Re-queue All
              </button>
              <button
                type="button"
                class="dm-ghost-btn dm-ghost-btn--danger"
                on:click={clearFailed}
                disabled={isActionPending}
                title="Clear failed items"
              >
                Clear Failed
              </button>
            {:else if activeTab === 'active' && $downloadQueue.length > 0}
              <button
                type="button"
                class="dm-ghost-btn dm-ghost-btn--danger"
                on:click={clearAll}
                title="Clear entire queue and history"
              >
                Clear All
              </button>
            {/if}
          </div>
        </div>
      {/if}
    </div>

    <!-- Scrollable List Body -->
    <div class="dm-body">
      {#if visibleItems.length === 0}
        <div class="dm-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="dm-empty-icon">
            {#if activeTab === 'completed'}
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            {:else if activeTab === 'failed'}
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            {:else}
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            {/if}
          </svg>
          {#if normalizedQuery}
            <p class="dm-empty-title">No matching tracks</p>
            <p class="dm-empty-sub">Try clearing the filter to view all {currentRawItems.length} items.</p>
          {:else if activeTab === 'active'}
            <p class="dm-empty-title">Queue is idle</p>
            <p class="dm-empty-sub">Queued and in-flight downloads will appear here.</p>
          {:else if activeTab === 'failed'}
            <p class="dm-empty-title">No failed downloads</p>
            <p class="dm-empty-sub">Tracks that could not be matched or transferred appear here.</p>
          {:else}
            <p class="dm-empty-title">No completed downloads yet</p>
            <p class="dm-empty-sub">Successfully downloaded tracks will be listed here.</p>
          {/if}
        </div>
      {:else}
        <ul class="dm-list">
          {#each visibleItems as item (item.id)}
            {@const statusUpper = String(item.status || '').toUpperCase()}
            {@const tone = statusTone(item.status)}
            {@const reasonText = item.error_reason || item.cancellation_reason || ''}
            <li class="dm-row">
              <div class="dm-row-main">
                <div class="dm-row-info">
                  <div class="dm-track-title" title={item.title || item.raw_title || ''}>
                    {item.title || item.raw_title || 'Untitled Track'}
                  </div>
                  <div class="dm-track-meta">
                    {#if item.artist}
                      <span class="dm-artist">{item.artist}</span>
                    {/if}
                    {#if item.artist && item.album}
                      <span class="dm-sep">·</span>
                    {/if}
                    {#if item.album}
                      <span class="dm-album">{item.album}</span>
                    {/if}
                  </div>
                </div>

                <span class="dm-status dm-status--{tone}">
                  <span class="dm-status-dot"></span>
                  <span>{statusLabel(item.status)}</span>
                </span>
              </div>

              {#if activeTab === 'active' && (statusUpper === 'DOWNLOADING' || (item.progress_percent || 0) > 0)}
                <div class="dm-progress-block">
                  <div class="dm-progress-track">
                    <div
                      class="dm-progress-fill"
                      style="width: {Math.min(100, Math.max(2, item.progress_percent || 0))}%"
                    ></div>
                  </div>
                  <div class="dm-progress-meta">
                    <span>{Math.round(item.progress_percent || 0)}%</span>
                    <span>{formatSpeed(item.current_speed)}</span>
                  </div>
                </div>
              {/if}

              {#if activeTab === 'failed' && reasonText}
                <p class="dm-reason">{reasonText}</p>
              {/if}

              <div class="dm-row-footer">
                <div class="dm-row-tags">
                  {#if activeTab === 'active'}
                    {#if item.provider_id}
                      <span class="dm-tag">{item.provider_id}</span>
                    {/if}
                    {#if item.retry_count > 0}
                      <span class="dm-tag dm-tag--warn">Attempt #{item.retry_count + 1}</span>
                    {/if}
                  {:else}
                    <span class="dm-time">{formatDate(item.updated_at || item.created_at)}</span>
                    {#if item.provider_id}
                      <span class="dm-tag">{item.provider_id}</span>
                    {/if}
                  {/if}
                </div>

                <div class="dm-row-actions">
                  {#if activeTab === 'active'}
                    {#if statusUpper === 'DOWNLOADING' || statusUpper === 'SEARCHING' || statusUpper === 'VERIFYING'}
                      <button
                        type="button"
                        class="dm-action-btn"
                        title="Pause download"
                        aria-label="Pause download"
                        on:click={() => pauseItem(item)}
                      >
                        Pause
                      </button>
                    {:else}
                      <button
                        type="button"
                        class="dm-action-btn dm-action-btn--primary"
                        title="Attempt download now"
                        aria-label="Attempt download now"
                        on:click={() => startNowItem(item)}
                      >
                        Start
                      </button>
                    {/if}
                  {:else if activeTab === 'failed'}
                    <button
                      type="button"
                      class="dm-action-btn"
                      title="Re-queue download"
                      aria-label="Re-queue download"
                      on:click={() => requeueItem(item)}
                    >
                      Re-queue
                    </button>
                    <button
                      type="button"
                      class="dm-action-btn dm-action-btn--primary"
                      title="Retry download immediately"
                      aria-label="Retry Now"
                      on:click={() => startNowItem(item)}
                    >
                      Retry
                    </button>
                  {:else}
                    <button
                      type="button"
                      class="dm-action-btn"
                      title="Re-download track"
                      aria-label="Re-download track"
                      on:click={() => requeueItem(item)}
                    >
                      Re-queue
                    </button>
                  {/if}

                  <button
                    type="button"
                    class="dm-remove-btn"
                    title="Remove record"
                    aria-label="Remove download"
                    on:click={() => deleteItem(item)}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" class="dm-svg-xs">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </aside>
{/if}

<style>
  .dm-backdrop {
    position: fixed;
    inset: 0;
    z-index: 50;
    background: color-mix(in srgb, var(--bg-canvas) 72%, transparent);
    backdrop-filter: blur(2px);
    display: none;
  }

  @media (min-width: 768px) {
    .dm-backdrop {
      display: block;
    }
  }

  .dm-drawer {
    position: fixed;
    inset: 0;
    z-index: 51;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--bg-surface);
    color: var(--text-primary);
    box-shadow: var(--shadow);
  }

  @media (min-width: 768px) {
    .dm-drawer {
      inset: 0 0 0 auto;
      width: 420px;
      border-left: 1px solid var(--border-subtle);
    }
  }

  @media (min-width: 1024px) {
    .dm-drawer {
      width: 460px;
    }
  }

  /* Header */
  .dm-header {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px 18px 14px;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
    user-select: none;
  }

  .dm-header-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .dm-title-group {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .dm-title {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
    line-height: 1.25;
  }

  .dm-subtitle {
    margin: 2px 0 0;
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 5px;
    font-variant-numeric: tabular-nums;
  }

  .dm-speed-inline {
    color: var(--color-primary);
    font-weight: 500;
  }

  .dm-sep {
    opacity: 0.45;
  }

  .dm-text-danger {
    color: var(--color-danger);
  }

  .dm-text-success {
    color: var(--success);
  }

  .dm-header-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .dm-primary-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 12px;
    border-radius: 8px;
    border: 1px solid transparent;
    background: var(--color-primary);
    color: var(--color-on-primary);
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.15s ease, opacity 0.15s ease;
  }

  .dm-primary-btn:hover:not(:disabled) {
    background: var(--color-primary-hover);
  }

  .dm-primary-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .dm-dot {
    width: 6px;
    height: 6px;
    border-radius: 9999px;
    background: currentColor;
  }

  .dm-dot--live {
    opacity: 0.9;
  }

  .dm-icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .dm-icon-btn:hover {
    background: var(--bg-surface-elevated);
    color: var(--text-primary);
  }

  .dm-mobile-back {
    display: inline-flex;
  }

  .dm-desktop-close {
    display: none;
  }

  @media (min-width: 768px) {
    .dm-mobile-back {
      display: none;
    }
    .dm-desktop-close {
      display: inline-flex;
    }
  }

  .dm-svg {
    width: 18px;
    height: 18px;
  }

  .dm-svg-sm {
    width: 13px;
    height: 13px;
  }

  .dm-svg-xs {
    width: 14px;
    height: 14px;
  }

  /* Quality Profile Row */
  .dm-profile-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .dm-profile-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    flex-shrink: 0;
  }

  .dm-select {
    flex: 1;
    max-width: 260px;
    height: 30px;
    padding: 0 10px;
    border-radius: 7px;
    border: 1px solid var(--border-subtle);
    background: var(--bg-input);
    color: var(--text-primary);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    outline: none;
    transition: border-color 0.15s ease;
  }

  .dm-select:focus {
    border-color: var(--color-primary);
  }

  /* Metrics Strip */
  .dm-metrics {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    border-bottom: 1px solid var(--border-subtle);
    background: var(--bg-canvas);
    flex-shrink: 0;
  }

  .dm-metric {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 9px 4px;
    gap: 2px;
    border-right: 1px solid var(--border-subtle);
  }

  .dm-metric:last-child {
    border-right: none;
  }

  .dm-metric-label {
    font-size: 10px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .dm-metric-val {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
    font-variant-numeric: tabular-nums;
  }

  .dm-metric-val--primary {
    color: var(--color-primary);
  }

  .dm-metric-val--danger {
    color: var(--color-danger);
  }

  .dm-metric-val--success {
    color: var(--success);
  }

  /* Tabs & Contextual Toolbar */
  .dm-controls {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px 18px;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border-subtle);
    flex-shrink: 0;
  }

  .dm-tabs {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 4px;
    padding: 3px;
    border-radius: 9px;
    background: var(--bg-canvas);
    border: 1px solid var(--border-subtle);
  }

  .dm-tab {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 30px;
    padding: 0 8px;
    border-radius: 6px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .dm-tab:hover {
    color: var(--text-primary);
  }

  .dm-tab--active {
    background: var(--bg-surface-elevated);
    color: var(--text-primary);
    font-weight: 600;
  }

  .dm-tab-count {
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    padding: 1px 6px;
    border-radius: 9999px;
    background: color-mix(in srgb, var(--text-muted) 14%, transparent);
    color: var(--text-secondary);
  }

  .dm-tab-count--danger {
    background: color-mix(in srgb, var(--color-danger) 14%, transparent);
    color: var(--color-danger);
  }

  .dm-tab-count--success {
    background: color-mix(in srgb, var(--success) 14%, transparent);
    color: var(--success);
  }

  .dm-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .dm-toolbar-spacer {
    flex: 1;
  }

  .dm-search-wrap {
    position: relative;
    flex: 1;
    min-width: 0;
  }

  .dm-search-icon {
    position: absolute;
    left: 9px;
    top: 50%;
    transform: translateY(-50%);
    width: 13px;
    height: 13px;
    color: var(--text-muted);
    pointer-events: none;
  }

  .dm-search-input {
    width: 100%;
    height: 28px;
    padding: 0 10px 0 28px;
    border-radius: 7px;
    border: 1px solid var(--border-subtle);
    background: var(--bg-input);
    color: var(--text-primary);
    font-size: 12px;
    outline: none;
    transition: border-color 0.15s ease;
  }

  .dm-search-input::placeholder {
    color: var(--text-muted);
  }

  .dm-search-input:focus {
    border-color: var(--color-primary);
  }

  .dm-bulk-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .dm-ghost-btn {
    height: 28px;
    padding: 0 10px;
    border-radius: 7px;
    border: 1px solid var(--border-subtle);
    background: transparent;
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  }

  .dm-ghost-btn:hover:not(:disabled) {
    background: var(--bg-surface-elevated);
    color: var(--text-primary);
  }

  .dm-ghost-btn--danger:hover:not(:disabled) {
    border-color: color-mix(in srgb, var(--color-danger) 40%, transparent);
    background: color-mix(in srgb, var(--color-danger) 10%, transparent);
    color: var(--color-danger);
  }

  .dm-ghost-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  /* Scrollable Body */
  .dm-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    background: var(--bg-canvas);
  }

  .dm-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 56px 24px;
    gap: 6px;
  }

  .dm-empty-icon {
    width: 28px;
    height: 28px;
    color: var(--text-muted);
    opacity: 0.55;
    margin-bottom: 4px;
  }

  .dm-empty-title {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .dm-empty-sub {
    margin: 0;
    font-size: 12px;
    color: var(--text-muted);
    max-width: 260px;
  }

  /* Minimalist Row List */
  .dm-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .dm-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 18px;
    border-bottom: 1px solid var(--border-subtle);
    background: transparent;
    transition: background-color 0.12s ease;
  }

  .dm-row:hover {
    background: color-mix(in srgb, var(--bg-surface-elevated) 45%, transparent);
  }

  .dm-row-main {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }

  .dm-row-info {
    flex: 1;
    min-width: 0;
  }

  .dm-track-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.3;
  }

  .dm-track-meta {
    margin-top: 2px;
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .dm-artist {
    color: var(--text-secondary);
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .dm-album {
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Restrained Status Indicator */
  .dm-status {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 6px;
    flex-shrink: 0;
    background: color-mix(in srgb, var(--text-muted) 10%, transparent);
    color: var(--text-secondary);
  }

  .dm-status-dot {
    width: 5px;
    height: 5px;
    border-radius: 9999px;
    background: currentColor;
  }

  .dm-status--primary {
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    color: var(--color-primary);
  }

  .dm-status--success {
    background: color-mix(in srgb, var(--success) 12%, transparent);
    color: var(--success);
  }

  .dm-status--warning {
    background: color-mix(in srgb, var(--color-warning) 12%, transparent);
    color: var(--color-warning);
  }

  .dm-status--danger {
    background: color-mix(in srgb, var(--color-danger) 12%, transparent);
    color: var(--color-danger);
  }

  /* Flat Progress Bar */
  .dm-progress-block {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .dm-progress-track {
    width: 100%;
    height: 3px;
    border-radius: 9999px;
    background: var(--bg-surface-elevated);
    overflow: hidden;
  }

  .dm-progress-fill {
    height: 100%;
    border-radius: 9999px;
    background: var(--color-primary);
    transition: width 0.25s ease;
  }

  .dm-progress-meta {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }

  /* Error Reason */
  .dm-reason {
    margin: 0;
    padding: 6px 8px;
    border-radius: 6px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.4;
    word-break: break-word;
  }

  /* Row Footer */
  .dm-row-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .dm-row-tags {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }

  .dm-time {
    font-size: 11px;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }

  .dm-tag {
    font-size: 10px;
    font-weight: 500;
    padding: 1px 6px;
    border-radius: 4px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  .dm-tag--warn {
    color: var(--color-warning);
    border-color: color-mix(in srgb, var(--color-warning) 28%, transparent);
  }

  .dm-row-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .dm-action-btn {
    height: 26px;
    padding: 0 9px;
    border-radius: 6px;
    border: 1px solid var(--border-subtle);
    background: var(--bg-surface);
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  }

  .dm-action-btn:hover {
    background: var(--bg-surface-elevated);
    color: var(--text-primary);
  }

  .dm-action-btn--primary {
    border-color: color-mix(in srgb, var(--color-primary) 35%, transparent);
    color: var(--color-primary);
  }

  .dm-action-btn--primary:hover {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: var(--color-on-primary);
  }

  .dm-remove-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 6px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .dm-remove-btn:hover {
    background: color-mix(in srgb, var(--color-danger) 12%, transparent);
    color: var(--color-danger);
  }
</style>
