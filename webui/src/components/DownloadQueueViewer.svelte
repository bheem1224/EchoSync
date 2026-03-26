<script>
  import { onMount, onDestroy } from 'svelte';
  import apiClient from '../api/client';
  import { feedback } from '../stores/feedback';

  let queueItems = [];
  let loading = true;
  let refreshInterval;
  let selectedIds = new Set();
  let selectAll = false;

  // Completed/failed rows are shown briefly then evicted so they never appear
  // frozen in the active queue.
  const STALE_TERMINAL_MS = 5000;
  const TERMINAL_STATUSES = new Set(['COMPLETED', 'FAILED', 'completed', 'failed']);

  function isActiveItem(item) {
    if (!TERMINAL_STATUSES.has(item.status)) return true;
    const finishedAt = item.updated_at ? new Date(item.updated_at).getTime() : 0;
    return Date.now() - finishedAt < STALE_TERMINAL_MS;
  }

  // Status colors
  const statusColors = {
    QUEUED: '#6366f1',
    SEARCHING: '#f59e0b',
    DOWNLOADING: '#3b82f6',
    COMPLETED: '#10b981',
    FAILED: '#ef4444',
    'NOT_FOUND': '#f97316',
    UNKNOWN: '#6b7280'
  };

  onMount(async () => {
    await loadQueue();
    // Refresh every 5 seconds
    refreshInterval = setInterval(loadQueue, 5000);
  });

  onDestroy(() => {
    if (refreshInterval) clearInterval(refreshInterval);
  });

  async function loadQueue() {
    try {
      const response = await apiClient.get('/downloads/queue');
      if (response.data && response.data.items) {
        // Replace the array reference so Svelte detects the change, and strip
        // terminal jobs that have been finished long enough to be considered stale.
        queueItems = response.data.items
          .map(item => ({ ...item, selected: selectedIds.has(item.id) }))
          .filter(isActiveItem);

        // Evict selections for items that no longer exist in the visible list.
        const visibleIds = new Set(queueItems.map(i => i.id));
        const pruned = new Set([...selectedIds].filter(id => visibleIds.has(id)));
        if (pruned.size !== selectedIds.size) {
          selectedIds = pruned;
        }
      }
      loading = false;
    } catch (error) {
      console.error('Failed to load queue:', error);
      feedback.addToast('Failed to load download queue', 'error');
      loading = false;
    }
  }

  function toggleSelection(id) {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    selectedIds = next;
    updateSelectAll();
  }

  function toggleSelectAll() {
    if (selectAll) {
      selectedIds = new Set(queueItems.map(item => item.id));
    } else {
      selectedIds = new Set();
    }
  }

  function updateSelectAll() {
    selectAll = queueItems.length > 0 && queueItems.every(item => selectedIds.has(item.id));
  }

  async function searchSelected() {
    if (selectedIds.size === 0) {
      feedback.addToast('No items selected', 'warning');
      return;
    }

    const ids = Array.from(selectedIds);
    let successCount = 0;
    let failureCount = 0;

    // Search each selected item and continue even if one fails.
    for (const id of ids) {
      try {
        await apiClient.post(`/downloads/${id}/search`);
        successCount += 1;
      } catch (error) {
        failureCount += 1;
        console.error(`Error searching item ${id}:`, error);
      }
    }

    if (successCount > 0) {
      feedback.addToast(`Searching ${successCount} item${successCount > 1 ? 's' : ''}...`, 'success');
    }
    if (failureCount > 0) {
      feedback.addToast(`Failed to start search for ${failureCount} item${failureCount > 1 ? 's' : ''}`, 'error');
    }

    // Reload queue after a brief delay
    setTimeout(loadQueue, 1000);
  }

  async function deleteSelected() {
    if (selectedIds.size === 0) {
      feedback.addToast('No items selected', 'warning');
      return;
    }

    const confirmed = confirm(`Delete ${selectedIds.size} selected item${selectedIds.size > 1 ? 's' : ''}?`);
    if (!confirmed) return;

    const ids = Array.from(selectedIds);
    let successCount = 0;
    let failureCount = 0;

    // Delete each selected item and continue even if one fails.
    for (const id of ids) {
      try {
        await apiClient.delete(`/downloads/${id}`);
        selectedIds.delete(id);
        successCount += 1;
      } catch (error) {
        failureCount += 1;
        console.error(`Error deleting item ${id}:`, error);
      }
    }

    selectedIds = selectedIds;
    updateSelectAll();

    if (successCount > 0) {
      feedback.addToast(`Deleted ${successCount} item${successCount > 1 ? 's' : ''}`, 'success');
    }
    if (failureCount > 0) {
      feedback.addToast(`Failed to delete ${failureCount} item${failureCount > 1 ? 's' : ''}`, 'error');
    }

    // Reload queue
    await loadQueue();
  }

  function formatDate(isoString) {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  }
</script>

<style>
  .queue-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem;
  }

  .toolbar {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .toolbar button {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
  }

  .btn-search {
    background-color: #3b82f6;
    color: white;
  }

  .btn-search:hover:not(:disabled) {
    background-color: #2563eb;
  }

  .btn-delete {
    background-color: #ef4444;
    color: white;
  }

  .btn-delete:hover:not(:disabled) {
    background-color: #dc2626;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .queue-list {
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .queue-item {
    display: flex;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #e5e7eb;
    gap: 1rem;
    transition: background-color 0.2s;
  }

  .queue-item:hover {
    background-color: #f9fafb;
  }

  .queue-item:last-child {
    border-bottom: none;
  }

  .checkbox {
    width: 1.25rem;
    height: 1.25rem;
    cursor: pointer;
    accent-color: #3b82f6;
  }

  .item-info {
    flex: 1;
    min-width: 0;
  }

  .item-title {
    font-weight: 500;
    color: #1f2937;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .item-artist {
    font-size: 0.875rem;
    color: #6b7280;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
    color: white;
    min-width: 80px;
    justify-content: center;
  }

  .timestamp {
    font-size: 0.75rem;
    color: #9ca3af;
    min-width: 140px;
    text-align: right;
  }

  .empty-state {
    text-align: center;
    padding: 2rem;
    color: #6b7280;
  }

  .empty-state p {
    font-size: 0.875rem;
  }

  .header-checkbox {
    margin-right: 0.5rem;
  }

  .selection-info {
    font-size: 0.875rem;
    color: #6b7280;
  }
</style>

<div class="queue-container">
  <div class="toolbar">
    <div style="flex: 1;">
      {#if queueItems.length > 0}
        <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
          <input type="checkbox" class="header-checkbox" bind:checked={selectAll} on:change={toggleSelectAll} />
          <span class="selection-info">
            {selectedIds.size > 0 ? `${selectedIds.size} selected` : 'Select items'}
          </span>
        </label>
      {/if}
    </div>
    <button
      class="btn-search"
      disabled={selectedIds.size === 0}
      on:click={searchSelected}
      title={selectedIds.size === 0 ? 'Select items to search' : 'Search for selected items'}
    >
      Search Selected
    </button>
    <button
      class="btn-delete"
      disabled={selectedIds.size === 0}
      on:click={deleteSelected}
      title={selectedIds.size === 0 ? 'Select items to delete' : 'Delete selected items'}
    >
      Delete Selected
    </button>
  </div>

  {#if loading}
    <div class="empty-state">
      <p>Loading download queue...</p>
    </div>
  {:else if queueItems.length === 0}
    <div class="empty-state">
      <p>Download queue is empty</p>
    </div>
  {:else}
    <div class="queue-list">
      {#each queueItems as item (item.id)}
        <div class="queue-item">
          <input
            type="checkbox"
            class="checkbox"
            checked={selectedIds.has(item.id)}
            on:change={() => toggleSelection(item.id)}
          />
          <div class="item-info">
            <div class="item-title">{item.title}</div>
            <div class="item-artist">{item.artist}</div>
          </div>
          <div
            class="status-badge"
            style="background-color: {statusColors[item.status] || statusColors.UNKNOWN}"
          >
            {item.status}
          </div>
          <div class="timestamp">{formatDate(item.updated_at)}</div>
        </div>
      {/each}
    </div>
  {/if}
</div>
