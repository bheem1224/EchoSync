<script>
  import { onMount, onDestroy } from 'svelte';
  import apiClient from '../../api/client';
  import { feedback } from '../../stores/feedback';

  export let isOpen = false;

  let queueItems = [];
  let selectedTrackIds = [];
  let isLoading = false;
  let pollingInterval = null;
  let downloadManagerRunning = false;

  $: totalTracks = queueItems.length;
  $: completedCount = queueItems.filter(t => t.status === 'COMPLETED').length;
  $: searchingCount = queueItems.filter(t => t.status === 'SEARCHING').length;
  $: downloadingCount = queueItems.filter(t => t.status === 'DOWNLOADING').length;
  $: failedCount = queueItems.filter(t => t.status === 'FAILED' || t.status === 'NOT_FOUND').length;
  $: queuedCount = queueItems.filter(t => t.status === 'QUEUED').length;
  $: processedCount = completedCount + failedCount;
  $: progressPercent = totalTracks > 0 ? Math.round((processedCount / totalTracks) * 100) : 0;
  $: allSelected = queueItems.length > 0 && selectedTrackIds.length === queueItems.length;
  $: hasSelection = selectedTrackIds.length > 0;

  // Fetch queue and job status from backend
  async function fetchQueue() {
    if (isLoading) return;
    isLoading = true;

    try {
      // Fetch queue
      const response = await apiClient.get('/downloads/queue');
      if (response.data && response.data.items) {
        queueItems = response.data.items;
      }

      // Fetch job status
      try {
        const jobsResponse = await apiClient.get('/jobs');
        if (jobsResponse.data && jobsResponse.data.items) {
          const downloadJob = jobsResponse.data.items.find(j => j.name === 'download_manager');
          downloadManagerRunning = downloadJob ? downloadJob.running : false;
        }
      } catch (e) {
        console.debug('Failed to fetch job status:', e);
      }
    } catch (error) {
      console.error('Failed to fetch download queue:', error);
      feedback.error('Failed to load download queue');
    } finally {
      isLoading = false;
    }
  }

  // Run download manager
  async function startDownloadManager() {
    try {
      const response = await apiClient.post('/downloads/run');
      
      if (response.status === 409) {
        // Job is already running
        feedback.warning(response.data?.reason || 'Download manager is already running');
        return;
      }
      
      feedback.success('Download processing started');
      await fetchQueue(); // Refresh immediately after starting
    } catch (error) {
      // Check if it's a 409 conflict
      if (error.response?.status === 409) {
        feedback.warning(error.response?.data?.reason || 'Download manager is already running');
      } else {
        console.error('Failed to start download manager:', error);
        feedback.error('Failed to start download manager');
      }
    }
  }

  // Delete selected tracks
  async function deleteSelected() {
    if (selectedTrackIds.length === 0) return;

    try {
      await apiClient.delete('/downloads/batch', {
        data: { ids: selectedTrackIds }
      });
      feedback.success(`Deleted ${selectedTrackIds.length} track(s)`);
      selectedTrackIds = [];
      await fetchQueue();
    } catch (error) {
      console.error('Failed to delete selected tracks:', error);
      feedback.error('Failed to delete selected tracks');
    }
  }

  // Search selected tracks
  async function searchSelected() {
    if (selectedTrackIds.length === 0) return;

    try {
      // Trigger search for each selected track
      for (const trackId of selectedTrackIds) {
        await apiClient.post(`/downloads/${trackId}/search`);
      }
      feedback.success(`Searching ${selectedTrackIds.length} track(s)`);
      selectedTrackIds = [];
      await fetchQueue(); // Refresh to show updated status
    } catch (error) {
      console.error('Failed to search selected tracks:', error);
      feedback.error('Failed to search selected tracks');
    }
  }

  // Clear entire queue
  async function clearQueue() {
    if (!confirm('Are you sure you want to clear the entire download queue?')) {
      return;
    }

    try {
      await apiClient.delete('/downloads/queue');
      feedback.success('Download queue cleared');
      selectedTrackIds = [];
      await fetchQueue();
    } catch (error) {
      console.error('Failed to clear queue:', error);
      feedback.error('Failed to clear queue');
    }
  }

  // Toggle all checkboxes
  function toggleSelectAll() {
    if (allSelected) {
      selectedTrackIds = [];
    } else {
      selectedTrackIds = queueItems.map(t => t.id);
    }
  }

  // Get status icon and color
  function getStatusDisplay(status) {
    switch (status) {
      case 'QUEUED':
        return { icon: '⏸️', color: 'text-gray-500', label: 'Queued' };
      case 'SEARCHING':
        return { icon: '🔍', color: 'text-blue-500 animate-pulse', label: 'Searching' };
      case 'DOWNLOADING':
        return { icon: '⬇️', color: 'text-indigo-500 animate-pulse', label: 'Downloading' };
      case 'COMPLETED':
        return { icon: '✅', color: 'text-green-500', label: 'Completed' };
      case 'NOT_FOUND':
        return { icon: '❌', color: 'text-orange-500', label: 'Not Found' };
      case 'FAILED':
        return { icon: '⛔', color: 'text-red-500', label: 'Failed' };
      default:
        return { icon: '❓', color: 'text-gray-400', label: status };
    }
  }

  // Start polling when drawer opens
  $: if (isOpen) {
    fetchQueue();
    if (!pollingInterval) {
      pollingInterval = setInterval(fetchQueue, 3000); // Poll every 3 seconds
    }
  } else {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  onDestroy(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
  });

  // Close drawer on Escape key
  function handleKeydown(event) {
    if (event.key === 'Escape' && isOpen) {
      isOpen = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<!-- Backdrop overlay -->
{#if isOpen}
  <div
    class="fixed inset-0 z-40 bg-black/50 transition-opacity"
    role="button"
    tabindex="0"
    on:click={() => isOpen = false}
    on:keydown={(e) => e.key === 'Enter' && (isOpen = false)}
  ></div>
{/if}

<!-- Slide-out drawer / modal -->
<div
  class="fixed top-0 right-0 h-full w-full md:w-2/3 lg:w-1/2 bg-gray-900 shadow-2xl z-50 transform transition-transform duration-300 ease-in-out flex flex-col cursor-default"
  class:translate-x-full={!isOpen}
  class:translate-x-0={isOpen}
>
  <!-- Header -->
  <div class="flex items-center justify-between p-4 border-b border-gray-700">
    <h2 class="text-xl font-bold text-white">Download Queue</h2>
    <button
      on:click={() => isOpen = false}
      class="text-gray-400 hover:text-white transition-colors p-2 rounded-lg hover:bg-gray-800"
      title="Close"
    >
      ✕
    </button>
  </div>

  <!-- Global Progress Bar -->
  <div class="px-4 pt-4 pb-2 bg-gray-850">
    <div class="flex justify-between items-center mb-2">
      <span class="text-sm text-gray-400">Overall Progress</span>
      <span class="text-sm font-semibold text-white">{progressPercent}%</span>
    </div>
    <div class="w-full bg-gray-700 rounded-full h-2.5 overflow-hidden">
      <div
        class="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
        style="width: {progressPercent}%"
      ></div>
    </div>
  </div>

  <!-- Stats -->
  <div class="grid grid-cols-5 gap-2 px-4 py-3 bg-gray-850 border-b border-gray-700">
    <div class="text-center">
      <div class="text-lg font-bold text-white">{totalTracks}</div>
      <div class="text-xs text-gray-400">Total</div>
    </div>
    <div class="text-center">
      <div class="text-lg font-bold text-gray-400">{queuedCount}</div>
      <div class="text-xs text-gray-400">Queued</div>
    </div>
    <div class="text-center">
      <div class="text-lg font-bold text-blue-400">{searchingCount}</div>
      <div class="text-xs text-gray-400">Searching</div>
    </div>
    <div class="text-center">
      <div class="text-lg font-bold text-orange-400">{failedCount}</div>
      <div class="text-xs text-gray-400">Failed</div>
    </div>
    <div class="text-center">
      <div class="text-lg font-bold text-green-400">{completedCount}</div>
      <div class="text-xs text-gray-400">Done</div>
    </div>
  </div>

  <!-- Action Bar -->
  <div class="flex gap-2 px-4 py-3 bg-gray-850 border-b border-gray-700">
    <button
      on:click={startDownloadManager}
      class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      disabled={isLoading || downloadManagerRunning}
      title={downloadManagerRunning ? 'Download manager is already running' : 'Start download processing'}
    >
      <span>{downloadManagerRunning ? '⏱️' : '▶️'}</span>
      <span>{downloadManagerRunning ? 'Running...' : 'Run Queue'}</span>
    </button>

    <button
      on:click={searchSelected}
      class="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      disabled={!hasSelection || isLoading}
      title="Search for selected items"
    >
      <span>🔍</span>
      <span>Search Selected</span>
    </button>

    <button
      on:click={deleteSelected}
      class="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      disabled={!hasSelection || isLoading}
    >
      <span>🗑️</span>
      <span>Delete Selected</span>
    </button>

    <button
      on:click={clearQueue}
      class="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors font-medium"
      disabled={totalTracks === 0 || isLoading}
    >
      <span>❌</span>
      <span>Clear Queue</span>
    </button>
  </div>

  <!-- Queue List -->
  <div class="flex-1 overflow-y-auto px-4 py-4 space-y-2">
    {#if isLoading && queueItems.length === 0}
      <div class="text-center py-8 text-gray-400">
        <div class="animate-spin text-3xl mb-2">⏳</div>
        <div>Loading queue...</div>
      </div>
    {:else if queueItems.length === 0}
      <div class="text-center py-8 text-gray-400">
        <div class="text-3xl mb-2">📭</div>
        <div>Download queue is empty</div>
      </div>
    {:else}
      <!-- Select All Checkbox -->
      <div class="flex items-center gap-3 p-3 bg-gray-800 rounded-lg mb-2 border border-gray-700">
        <input
          type="checkbox"
          checked={allSelected}
          on:change={toggleSelectAll}
          class="w-4 h-4 rounded border-gray-600 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-gray-900 cursor-pointer"
        />
        <span class="text-sm text-gray-300 font-medium">
          {#if allSelected}
            Deselect All
          {:else}
            Select All ({totalTracks})
          {/if}
        </span>
      </div>

      <!-- Track Items -->
      {#each queueItems as track (track.id)}
        {@const statusDisplay = getStatusDisplay(track.status)}
        <div
          class="flex items-center gap-3 p-3 bg-gray-800 hover:bg-gray-750 rounded-lg transition-colors border border-gray-700"
        >
          <!-- Checkbox -->
          <input
            type="checkbox"
            value={track.id}
            bind:group={selectedTrackIds}
            class="w-4 h-4 rounded border-gray-600 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-gray-900 cursor-pointer"
          />

          <!-- Status Icon -->
          <div class="text-2xl {statusDisplay.color}" title={statusDisplay.label}>
            {statusDisplay.icon}
          </div>

          <!-- Track Info -->
          <div class="flex-1 min-w-0">
            <div class="text-white font-medium truncate">{track.title}</div>
            <div class="text-sm text-gray-400 truncate">{track.artist}</div>
            {#if track.album}
              <div class="text-xs text-gray-500 truncate">{track.album}</div>
            {/if}
          </div>

          <!-- Status Badge -->
          <div class="flex-shrink-0">
            <span
              class="px-2 py-1 text-xs font-medium rounded-full {statusDisplay.color} bg-gray-700"
            >
              {statusDisplay.label}
            </span>
          </div>
        </div>
      {/each}
    {/if}
  </div>

  <!-- Footer with refresh note -->
  <div class="px-4 py-3 bg-gray-850 border-t border-gray-700 text-xs text-gray-500 text-center">
    Auto-refreshing every 3 seconds • {selectedTrackIds.length} selected
  </div>
</div>

<style>
  .bg-gray-850 {
    background-color: #1a1d23;
  }
  
  .bg-gray-750 {
    background-color: #2d3238;
  }
</style>
