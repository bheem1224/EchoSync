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

  let activeTab = 'active'; // 'active' | 'history'
  let isActionPending = false;
  let pollIntervalId = null;

  // Quality Profiles
  let qualityProfiles = [];
  let selectedProfileId = '';

  // Format bytes per second
  function formatSpeed(bytesPerSec) {
    if (!bytesPerSec || isNaN(bytesPerSec) || bytesPerSec <= 0) return '0 KB/s';
    const kb = bytesPerSec / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB/s`;
    const mb = kb / 1024;
    return `${mb.toFixed(2)} MB/s`;
  }

  // Format timestamp
  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '';
    }
  }

  async function loadQualityProfiles() {
    try {
      const resp = await apiClient.get('/system/config/quality-profiles').catch(() => apiClient.get('/system/quality-profiles'));
      const profiles = resp.data?.profiles || [];
      qualityProfiles = Array.isArray(profiles) ? profiles : [];
      
      const saved = localStorage.getItem('echosync.active_quality_profile');
      if (saved && qualityProfiles.some(p => String(p.id) === String(saved))) {
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
      const selected = qualityProfiles.find(p => String(p.id) === String(selectedProfileId));
      if (selected) {
        feedback.info(`Active Quality Profile: ${selected.name || selectedProfileId}`);
      }
    } catch (err) {
      console.error(err);
    }
  }

  // Lock background scrolling on mobile/desktop viewports when drawer is open
  $: if (typeof document !== 'undefined') {
    document.body.classList.toggle('overflow-hidden', $isDownloadDrawerOpen);
  }

  // Start polling when drawer is open
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

  // Action: Trigger download processing now
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

  // Action: Start/Attempt Now
  async function startNowItem(item) {
    try {
      await apiClient.post(`/core/downloads/${item.id}/start-now`);
      feedback.success(`Started "${item.title || item.raw_title || 'track'}"`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to start download: ${err.response?.data?.detail || err.message}`);
    }
  }

  // Action: Passive Re-queue (move to queue without immediately executing)
  async function requeueItem(item) {
    try {
      await apiClient.post(`/core/downloads/${item.id}/requeue`);
      feedback.success(`Re-queued "${item.title || item.raw_title || 'track'}"`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to re-queue download: ${err.response?.data?.detail || err.message}`);
    }
  }

  // Action: Pause an item
  async function pauseItem(item) {
    try {
      await apiClient.post(`/core/downloads/${item.id}/pause`);
      feedback.info(`Paused "${item.title || item.raw_title || 'track'}"`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to pause download: ${err.response?.data?.detail || err.message}`);
    }
  }

  // Action: Delete/Remove an item
  async function deleteItem(item) {
    try {
      await apiClient.delete(`/core/downloads/${item.id}`);
      feedback.success(`Removed "${item.title || item.raw_title || 'track'}"`);
      await fetchDownloads();
    } catch (err) {
      feedback.error(`Failed to remove download: ${err.response?.data?.detail || err.message}`);
    }
  }

  // Action: Bulk Re-queue All Failed
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

  // Action: Bulk Clear Failed
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

  // Action: Clear entire queue
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
  <!-- Backdrop (Desktop only or overlay) -->
  <div 
    class="drawer-backdrop fixed inset-0 bg-black/60 backdrop-blur-sm z-50 transition-opacity hidden md:block"
    on:click={closeDownloadDrawer}
    transition:fade={{ duration: 200 }}
    aria-hidden="true"
  ></div>

  <!-- Responsive Drawer Viewport -->
  <aside 
    class="drawer-panel fixed inset-0 md:inset-y-0 md:left-auto md:right-0 z-50 w-full h-full md:w-96 lg:w-[500px] bg-base-100 bg-surface text-text-primary flex flex-col shadow-2xl md:border-l border-base-300 border-border-subtle overflow-hidden"
    transition:fly={{ x: 500, duration: 250 }}
    aria-label="Download Manager Drawer"
  >
    <!-- Sticky Responsive Header -->
    <div class="sticky top-0 z-20 flex flex-col gap-3 p-4 border-b border-base-300 border-border-subtle bg-surface bg-base-100 select-none">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <!-- Mobile Back Button -->
          <button 
            class="btn btn-ghost btn-sm md:hidden min-w-[44px] min-h-[44px] flex items-center justify-center p-2 rounded-xl bg-surface-hover/50 active:scale-95 text-text-primary" 
            on:click={closeDownloadDrawer}
            aria-label="Back"
            title="Back"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
          </button>

          <div class="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 hidden sm:flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
          </div>

          <div>
            <h2 class="text-base sm:text-lg font-bold tracking-tight">Download Manager</h2>
            <p class="text-xs text-text-muted">
              {#if $downloadStats.totalSpeed > 0}
                <span class="text-emerald-400 font-semibold">⚡ {formatSpeed($downloadStats.totalSpeed)}</span> • 
              {/if}
              {$activeDownloads.length} active item{$activeDownloads.length === 1 ? '' : 's'}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <!-- Process Now Action -->
          <button
            class="btn-run px-3.5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 active:scale-95 transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50 min-h-[44px] sm:min-h-[36px]"
            on:click={triggerRun}
            disabled={isActionPending}
            title="Process all queued downloads now"
          >
            {#if $downloadStats.isRunning}
              <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              Running
            {:else}
              <span>▶</span> <span class="hidden xs:inline">Process Now</span>
            {/if}
          </button>

          <!-- Desktop Close Button -->
          <button 
            class="btn btn-ghost btn-sm hidden md:flex min-w-[36px] min-h-[36px] items-center justify-center p-2 rounded-lg hover:bg-surface-hover active:scale-95 text-text-muted hover:text-text-primary transition-all" 
            on:click={closeDownloadDrawer}
            aria-label="Close Drawer"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Top Bar Quality Profile Selector -->
      {#if qualityProfiles && qualityProfiles.length > 0}
        <div class="flex items-center justify-between gap-2 px-3 py-1.5 rounded-xl bg-surface-hover/30 border border-border-subtle/50 text-xs">
          <span class="text-text-muted font-medium flex items-center gap-1.5 shrink-0">
            <span>🎯 Quality Profile:</span>
          </span>
          <select 
            class="bg-surface/90 border border-border-subtle rounded-lg px-2.5 py-1 text-xs text-text-primary font-semibold focus:outline-none focus:border-indigo-500 transition-all cursor-pointer flex-1 max-w-[240px]"
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
    </div>

    <!-- Navigation Tabs & Stats Sub-header -->
    <div class="px-4 sm:px-6 pt-3 pb-2 border-b border-base-300 border-border-subtle bg-surface/50 bg-base-200/50 flex flex-col gap-3">
      <!-- Tabs & Tab-level Bulk Actions -->
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <button 
            class="tab-btn px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 min-h-[40px]"
            class:active={activeTab === 'active'}
            on:click={() => activeTab = 'active'}
          >
            <span>Active Queue</span>
            {#if $activeDownloads.length > 0}
              <span class="count-badge px-2 py-0.5 rounded-full text-[10px] bg-indigo-500 text-white font-bold">
                {$activeDownloads.length}
              </span>
            {/if}
          </button>

          <button 
            class="tab-btn px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 min-h-[40px]"
            class:active={activeTab === 'history'}
            on:click={() => activeTab = 'history'}
          >
            <span>History & Failed</span>
            {#if $downloadHistory.length > 0}
              <span class="count-badge px-2 py-0.5 rounded-full text-[10px] bg-surface-hover text-text-muted font-bold">
                {$downloadHistory.length}
              </span>
            {/if}
          </button>
        </div>

        {#if activeTab === 'history' && $downloadHistory.length > 0}
          <div class="flex items-center gap-1.5">
            <button 
              class="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 transition-all flex items-center gap-1 min-h-[36px]"
              on:click={requeueAllFailed}
              title="Re-queue all failed items"
            >
              <span>↺</span> <span class="hidden sm:inline">Re-queue All</span>
            </button>
            <button 
              class="px-2.5 py-1.5 rounded-lg text-xs font-medium bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition-all flex items-center gap-1 min-h-[36px]"
              on:click={clearFailed}
              title="Clear failed items"
            >
              <span>🗑</span> <span class="hidden sm:inline">Clear Failed</span>
            </button>
          </div>
        {:else if activeTab === 'active' && $downloadQueue.length > 0}
          <button 
            class="text-xs text-rose-400 hover:text-rose-300 hover:underline px-2 py-2 transition-all min-h-[40px] flex items-center ml-auto"
            on:click={clearAll}
            title="Clear all downloads"
          >
            Clear All
          </button>
        {/if}
      </div>

      <!-- Quick stats bar -->
      <div class="grid grid-cols-4 gap-2 text-center py-2 px-3 bg-surface-hover/30 rounded-xl border border-border-subtle/50 text-[11px]">
        <div>
          <div class="text-text-muted text-[10px] uppercase tracking-wider font-semibold">Speed</div>
          <div class="font-bold text-emerald-400">{formatSpeed($downloadStats.totalSpeed)}</div>
        </div>
        <div>
          <div class="text-text-muted text-[10px] uppercase tracking-wider font-semibold">Active</div>
          <div class="font-bold text-indigo-400">{$downloadStats.activeCount}</div>
        </div>
        <div>
          <div class="text-text-muted text-[10px] uppercase tracking-wider font-semibold">Queued</div>
          <div class="font-bold text-amber-400">{$downloadStats.queuedCount}</div>
        </div>
        <div>
          <div class="text-text-muted text-[10px] uppercase tracking-wider font-semibold">Completed</div>
          <div class="font-bold text-emerald-400">{$downloadStats.completedCount}</div>
        </div>
      </div>
    </div>

    <!-- Transfer List Container with Smooth Scrolling -->
    <div class="drawer-body flex-1 overflow-y-auto scroll-smooth p-4 sm:p-6 space-y-3">
      {#if activeTab === 'active'}
        {#if $activeDownloads.length === 0}
          <div class="empty-state py-16 text-center text-text-muted flex flex-col items-center justify-center gap-3">
            <div class="text-4xl opacity-40">📥</div>
            <p class="text-sm font-medium">No active downloads</p>
            <p class="text-xs text-text-muted max-w-xs">Search for tracks or sync playlists with download missing enabled to queue downloads.</p>
          </div>
        {:else}
          {#each $activeDownloads as item (item.id)}
            <div class="download-card p-3.5 sm:p-4 rounded-2xl border border-border-subtle bg-surface-hover/20 hover:bg-surface-hover/40 transition-all flex flex-col gap-2.5">
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <div class="font-bold text-sm text-text-primary truncate">
                    {#if item.artist}
                      {item.artist} <span class="text-text-muted font-normal">•</span> {item.title}
                    {:else}
                      {item.title}
                    {/if}
                  </div>
                  {#if item.album}
                    <div class="text-xs text-text-muted truncate mt-0.5">{item.album}</div>
                  {/if}
                </div>

                <div class="flex items-center gap-1.5 shrink-0">
                  <!-- Status Badge -->
                  <span 
                    class="status-pill px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                    class:status-downloading={String(item.status).toUpperCase() === 'DOWNLOADING'}
                    class:status-searching={String(item.status).toUpperCase() === 'SEARCHING'}
                    class:status-queued={String(item.status).toUpperCase() === 'QUEUED'}
                    class:status-paused={String(item.status).toUpperCase() === 'PAUSED'}
                  >
                    {#if String(item.status).toUpperCase() === 'DOWNLOADING'}
                      ⚡ Downloading
                    {:else if String(item.status).toUpperCase() === 'SEARCHING'}
                      🔍 Searching
                    {:else if String(item.status).toUpperCase() === 'PAUSED'}
                      ⏸ Paused
                    {:else}
                      ⏳ Queued
                    {/if}
                  </span>
                </div>
              </div>

              <!-- Animated Progress bar & metrics -->
              {#if String(item.status).toUpperCase() === 'DOWNLOADING' || item.progress_percent > 0}
                <div class="w-full space-y-1.5">
                  <div class="w-full h-2.5 rounded-full bg-surface-active overflow-hidden relative">
                    <div 
                      class="h-full rounded-full transition-all duration-300 relative overflow-hidden {item.current_speed > 0 ? 'bg-gradient-animated' : 'bg-gradient-to-r from-indigo-500 to-emerald-400'}"
                      style="width: {Math.max(3, item.progress_percent || 0)}%"
                    >
                      {#if item.current_speed > 0}
                        <div class="absolute inset-0 shimmer-overlay"></div>
                      {/if}
                    </div>
                  </div>
                  <div class="flex items-center justify-between text-[11px] text-text-muted font-medium">
                    <span>{Math.round(item.progress_percent || 0)}%</span>
                    <span class="text-emerald-400 font-semibold">{formatSpeed(item.current_speed)}</span>
                  </div>
                </div>
              {/if}

              <!-- Footer info & Card action buttons: [ ▶ Attempt Now / ⏸ Pause ] and [ ✕ Remove ] -->
              <div class="flex items-center justify-between pt-1 border-t border-border-subtle/40 text-[11px] text-text-muted">
                <div class="flex items-center gap-2">
                  {#if item.provider_id}
                    <span class="px-2 py-0.5 rounded bg-surface border border-border-subtle text-[10px] text-text-muted uppercase font-semibold">
                      {item.provider_id}
                    </span>
                  {/if}
                  {#if item.retry_count > 0}
                    <span class="text-amber-400 text-[10px] font-semibold">Retry #{item.retry_count}</span>
                  {/if}
                </div>

                <!-- Touch target controls: min-w-[44px] min-h-[44px] on mobile -->
                <div class="flex items-center gap-1.5">
                  {#if String(item.status).toUpperCase() === 'DOWNLOADING' || String(item.status).toUpperCase() === 'SEARCHING'}
                    <button 
                      class="min-w-[44px] min-h-[44px] sm:min-w-[34px] sm:min-h-[34px] px-2.5 py-1 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/20 flex items-center justify-center gap-1 font-semibold text-xs active:scale-90 transition-all" 
                      title="Pause download" 
                      on:click={() => pauseItem(item)}
                      aria-label="Pause download"
                    >
                      <span>⏸</span> <span class="hidden sm:inline">Pause</span>
                    </button>
                  {:else}
                    <button 
                      class="min-w-[44px] min-h-[44px] sm:min-w-[34px] sm:min-h-[34px] px-2.5 py-1 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 flex items-center justify-center gap-1 font-semibold text-xs active:scale-90 transition-all" 
                      title="Attempt Now" 
                      on:click={() => startNowItem(item)}
                      aria-label="Attempt download now"
                    >
                      <span>▶</span> <span class="hidden sm:inline">Attempt Now</span>
                    </button>
                  {/if}

                  <button 
                    class="min-w-[44px] min-h-[44px] sm:min-w-[34px] sm:min-h-[34px] px-2 py-1 rounded-xl hover:bg-rose-500/10 hover:text-rose-400 text-text-muted border border-border-subtle/50 flex items-center justify-center font-semibold text-xs active:scale-90 transition-all" 
                    title="Remove Download" 
                    on:click={() => deleteItem(item)}
                    aria-label="Remove download"
                  >
                    <span>✕</span>
                  </button>
                </div>
              </div>
            </div>
          {/each}
        {/if}
      {:else}
        <!-- History & Failed tab -->
        {#if $downloadHistory.length === 0}
          <div class="empty-state py-16 text-center text-text-muted flex flex-col items-center justify-center gap-3">
            <div class="text-4xl opacity-40">📜</div>
            <p class="text-sm font-medium">No history records</p>
            <p class="text-xs text-text-muted">Completed and failed downloads will appear here.</p>
          </div>
        {:else}
          {#each $downloadHistory as item (item.id)}
            <div class="history-card p-3.5 sm:p-4 rounded-2xl border border-border-subtle bg-surface-hover/10 hover:bg-surface-hover/30 transition-all flex flex-col gap-2">
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <div class="font-bold text-sm text-text-primary truncate">
                    {#if item.artist}
                      {item.artist} <span class="text-text-muted font-normal">•</span> {item.title}
                    {:else}
                      {item.title}
                    {/if}
                  </div>
                  {#if item.album}
                    <div class="text-xs text-text-muted truncate mt-0.5">{item.album}</div>
                  {/if}
                </div>

                <div class="flex items-center gap-2 shrink-0">
                  {#if String(item.status).toUpperCase() === 'COMPLETED'}
                    <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      ✓ Completed
                    </span>
                  {:else if String(item.status).toUpperCase() === 'CANCELLED'}
                    <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-zinc-500/10 text-zinc-400 border border-zinc-500/20">
                      Cancelled
                    </span>
                  {:else}
                    <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                      ✗ {String(item.status).toUpperCase() === 'NOT_FOUND' ? 'Not Found' : 'Failed'}
                    </span>
                  {/if}
                </div>
              </div>

              {#if item.cancellation_reason}
                <p class="text-[11px] text-zinc-400 italic bg-black/20 p-2 rounded-lg">
                  {item.cancellation_reason}
                </p>
              {/if}

              <!-- Card action buttons: [ ↺ Re-queue ], [ ⚡ Retry Now ], and [ ✕ Remove ] -->
              <div class="flex items-center justify-between text-[11px] text-text-muted pt-1.5 border-t border-border-subtle/30">
                <span>{formatDate(item.updated_at || item.created_at)}</span>
                <div class="flex items-center gap-1.5">
                  <button 
                    class="min-h-[44px] sm:min-h-[28px] px-2.5 py-1 rounded-lg bg-surface-hover hover:bg-indigo-600 hover:text-white text-text-primary transition-all text-xs font-semibold flex items-center gap-1 active:scale-95"
                    on:click={() => requeueItem(item)}
                    title="Re-queue download to queue (passive)"
                    aria-label="Re-queue download"
                  >
                    <span>↺</span> <span class="hidden sm:inline">Re-queue</span>
                  </button>
                  <button 
                    class="min-h-[44px] sm:min-h-[28px] px-2.5 py-1 rounded-lg bg-indigo-500/20 hover:bg-indigo-600 text-indigo-300 hover:text-white transition-all text-xs font-semibold flex items-center gap-1 active:scale-95 border border-indigo-500/30"
                    on:click={() => startNowItem(item)}
                    title="Attempt/Process download immediately"
                    aria-label="Retry Now"
                  >
                    <span>⚡</span> <span class="hidden sm:inline">Retry Now</span>
                  </button>
                  <button 
                    class="min-w-[44px] min-h-[44px] sm:min-w-[28px] sm:min-h-[28px] flex items-center justify-center p-1.5 rounded-lg hover:bg-surface-hover hover:text-rose-400 transition-all text-xs active:scale-95" 
                    title="Delete record" 
                    on:click={() => deleteItem(item)}
                    aria-label="Delete history record"
                  >
                    ✕
                  </button>
                </div>
              </div>
            </div>
          {/each}
        {/if}
      {/if}
    </div>
  </aside>
{/if}

<style>
  .drawer-panel {
    background: var(--surface, #181824);
  }
  .tab-btn {
    color: var(--muted, #94a3b8);
    background: transparent;
  }
  .tab-btn.active {
    background: var(--surface-active, rgba(255, 255, 255, 0.08));
    color: var(--text, #f8fafc);
  }
  .status-downloading {
    background: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    border: 1px solid rgba(99, 102, 241, 0.3);
  }
  .status-searching {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }
  .status-queued {
    background: rgba(148, 163, 184, 0.15);
    color: #cbd5e1;
    border: 1px solid rgba(148, 163, 184, 0.3);
  }
  .status-paused {
    background: rgba(234, 179, 8, 0.15);
    color: #fde047;
    border: 1px solid rgba(234, 179, 8, 0.3);
  }
  .bg-gradient-animated {
    background: linear-gradient(90deg, #6366f1 0%, #10b981 50%, #6366f1 100%);
    background-size: 200% 100%;
    animation: gradient-shift 2s linear infinite;
  }
  @keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
  }
  .shimmer-overlay {
    background: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0) 0%,
      rgba(255, 255, 255, 0.25) 50%,
      rgba(255, 255, 255, 0) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }
</style>
