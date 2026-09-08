<script>
  import apiClient from '../api/client';
  import { onMount, onDestroy } from 'svelte';
  import DuplicateCompareModal from './DuplicateCompareModal.svelte';
  
  let suggestions = [];
  let pendingActions = [];
  let activeTab = 'suggestions';
  let searchQuery = '';
  let queueFilterType = 'All';
  let queueFilterOriginator = 'All';
  let pollingHandle = null;

  let selectedDuplicate = null;
  let isCompareModalOpen = false;

  function decodeLabel(item) {
    return item?.title || item?.sync_id || 'Unknown';
  }

  function formatTrackBadge(track) {
    if (!track) return 'UNKNOWN';
    const fmt = (track.format || 'AUDIO').toUpperCase();
    const br = track.bitrate ? ` ${Math.round(track.bitrate / 1000)}k` : '';
    return `${fmt}${br}`;
  }

  async function fetchSuggestions() {
    try {
      const res = await apiClient.get('/system/manager/queue/suggestions');
      if (res.status === 200) {
        suggestions = res.data.suggestions || [];
      }
    } catch (e) {
      console.error('Failed to fetch suggestions:', e);
    }
  }

  async function fetchPendingActions() {
    try {
      const res = await apiClient.get('/system/manager/queue/actions');
      if (res.status === 200) {
        pendingActions = res.data.queue || [];
      }
    } catch (e) {
      console.error('Failed to fetch pending actions:', e);
    }
  }

  function _matchesSearch(item) {
    if (!searchQuery || !searchQuery.trim()) return true;
    const s = searchQuery.trim().toLowerCase();
    return (
      (item.title && item.title.toLowerCase().includes(s)) ||
      (item.artist && item.artist.toLowerCase().includes(s)) ||
      (item.sync_id && item.sync_id.toLowerCase().includes(s))
    );
  }

  $: filteredSuggestions = (suggestions || []).filter(
    d =>
      (queueFilterType === 'All' || d.type === queueFilterType) &&
      (queueFilterOriginator === 'All' || (d.originator || 'System') === queueFilterOriginator) &&
      _matchesSearch(d)
  );

  $: filteredPendingActions = (pendingActions || []).filter(
    i =>
      (queueFilterType === 'All' ||
        i.action_needed === queueFilterType ||
        (queueFilterType === 'Upgrade' && i.action_needed === 'UPGRADE_WEEK_END') ||
        (queueFilterType === 'Deletion' && i.action_needed === 'DELETE_MONTH_END')) &&
      (queueFilterOriginator === 'All' || (i.originator || 'System') === queueFilterOriginator) &&
      _matchesSearch(i)
  );

  onMount(() => {
    fetchSuggestions();
    fetchPendingActions();
    pollingHandle = setInterval(() => {
      fetchPendingActions();
      fetchSuggestions();
    }, 8000);
  });

  onDestroy(() => {
    if (pollingHandle) clearInterval(pollingHandle);
  });

  function openCompareModal(item) {
    if (item.winner_track || item.loser_track || item.type === 'HYGIENE_DUPLICATION') {
      selectedDuplicate = item;
      isCompareModalOpen = true;
    }
  }

  async function handleApproveDuplicate(item) {
    if (item.winner_track && item.loser_track) {
      try {
        await apiClient.post('/system/manager/conflicts/resolve', {
          keep_id: item.winner_track.id,
          delete_ids: [item.loser_track.id],
          sync_id: item.sync_id,
        });
        suggestions = suggestions.filter(s => s.sync_id !== item.sync_id);
      } catch (e) {
        console.error('Failed to approve duplicate:', e);
      }
    } else {
      openCompareModal(item);
    }
  }

  async function handleVeto(item) {
    try {
      await apiClient.post('/system/manager/veto', {
        sync_id: item.sync_id,
        reason: 'User vetoed duplicate suggestion',
      });
      suggestions = suggestions.filter(s => s.sync_id !== item.sync_id);
    } catch (e) {
      console.error('Failed to veto suggestion:', e);
    }
  }

  async function vetoPendingAction(item) {
    try {
      await apiClient.post('/system/manager/suggestion-candidates/override', {
        sync_id: item.sync_id,
        field: 'admin_exempt_deletion',
        value: true,
      });
      fetchPendingActions();
    } catch (e) {
      console.error(e);
    }
  }

  async function executeNow(item) {
    try {
      if (!item.track_id) {
        alert('No track id');
        return;
      }
      const endpoint =
        item.action_needed === 'DELETE_MONTH_END'
          ? `/api/v1/system/manager/track/${item.track_id}/force_delete`
          : `/api/v1/system/manager/track/${item.track_id}/force_upgrade`;
      await apiClient.post(endpoint);
      fetchPendingActions();
    } catch (e) {
      console.error(e);
    }
  }

  function handleModalResolved(event) {
    const detail = event.detail;
    if (detail?.sync_id) {
      suggestions = suggestions.filter(s => s.sync_id !== detail.sync_id);
    }
    fetchSuggestions();
    fetchPendingActions();
  }
</script>

<div class="flex flex-col gap-4">
  <!-- Top Search & Filter Bar -->
  <div class="flex items-center gap-4 mb-2">
    <input
      placeholder="Search by title, artist, or sync ID..."
      bind:value={searchQuery}
      class="flex-1 bg-black/20 border border-glass-border rounded-global px-3 py-1.5 text-sm outline-none focus:border-primary text-white"
    />
    <select
      bind:value={queueFilterType}
      class="bg-black/20 border border-glass-border rounded-global px-2 py-1.5 text-sm outline-none text-white"
    >
      <option>All</option>
      <option>Upgrade</option>
      <option>Deletion</option>
      <option>HYGIENE_DUPLICATION</option>
      <option>Duplicate Resolution</option>
    </select>
    <select
      bind:value={queueFilterOriginator}
      class="bg-black/20 border border-glass-border rounded-global px-2 py-1.5 text-sm outline-none text-white"
    >
      <option>All</option>
      <option>System</option>
      <option>User</option>
    </select>
  </div>

  <!-- Tabs Navigation -->
  <div class="flex gap-4 border-b border-glass-border pb-2">
    <button
      class="text-sm font-semibold transition-colors {activeTab === 'suggestions' ? 'text-primary border-b-2 border-primary -mb-[9px]' : 'text-muted hover:text-white'}"
      on:click={() => (activeTab = 'suggestions')}
    >
      Suggestions & Requests ({filteredSuggestions.length})
    </button>
    <button
      class="text-sm font-semibold transition-colors {activeTab === 'pending' ? 'text-primary border-b-2 border-primary -mb-[9px]' : 'text-muted hover:text-white'}"
      on:click={() => (activeTab = 'pending')}
    >
      Pending Actions ({filteredPendingActions.length})
    </button>
  </div>

  <!-- Queue Items List -->
  <div class="overflow-y-auto max-h-[500px] flex flex-col gap-2.5 pr-2 custom-scrollbar">
    {#if activeTab === 'suggestions'}
      {#if filteredSuggestions.length === 0}
        <div class="text-muted text-sm italic text-center py-12">No suggestions at this time.</div>
      {/if}
      {#each filteredSuggestions as item}
        <!-- Interactive Card Row -->
        <div
          class="flex flex-col gap-2.5 bg-black/20 hover:bg-black/30 p-3.5 rounded-global border border-glass-border hover:border-white/20 transition-all cursor-pointer group"
          on:click={() => openCompareModal(item)}
        >
          <div class="flex justify-between items-start gap-3">
            <div class="flex flex-col gap-1 min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-[10px] uppercase font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full">
                  {item.type}
                </span>
                {#if item.comparison_reason}
                  <span class="text-[10px] uppercase font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                    {item.comparison_reason}
                  </span>
                {/if}
                <span class="text-sm font-bold text-white group-hover:text-primary transition-colors truncate">
                  {decodeLabel(item)}
                </span>
              </div>
              <div class="flex items-center gap-2 text-xs text-muted">
                <span>Origin: {item.originator || 'System'}</span>
                {#if item.artist}
                  <span>&bull;</span>
                  <span>Artist: <strong class="text-white/80">{item.artist}</strong></span>
                {/if}
              </div>
            </div>

            <!-- Card Actions -->
            <div class="flex items-center gap-2 shrink-0" on:click|stopPropagation>
              {#if item.winner_track || item.loser_track}
                <button
                  class="bg-white/10 hover:bg-white/20 text-white text-xs font-bold px-2.5 py-1 rounded-global transition-colors"
                  on:click={() => openCompareModal(item)}
                  title="Open side-by-side comparison"
                >
                  Compare
                </button>
              {/if}
              <button
                class="bg-primary text-black text-xs font-bold px-3 py-1 rounded-global hover:scale-95 transition-transform"
                on:click={() => handleApproveDuplicate(item)}
              >
                Approve
              </button>
              <button
                class="bg-surface-hover text-white text-xs font-bold px-3 py-1 rounded-global hover:scale-95 transition-transform"
                on:click={() => handleVeto(item)}
              >
                Reject
              </button>
            </div>
          </div>

          <!-- Rich Format & File Path Preview -->
          {#if item.winner_track && item.loser_track}
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-1.5 border-t border-white/5">
              <div class="flex items-center gap-2 bg-emerald-950/25 border border-emerald-500/20 rounded-md p-2 min-w-0">
                <span class="text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/30 text-emerald-300 shrink-0">
                  KEEP
                </span>
                <span class="font-mono font-bold text-emerald-400 shrink-0">
                  {formatTrackBadge(item.winner_track)}
                </span>
                <span class="text-[11px] text-muted truncate font-mono" title={item.winner_track.file_path}>
                  {item.winner_track.file_path || 'Unknown Path'}
                </span>
              </div>

              <div class="flex items-center gap-2 bg-rose-950/25 border border-rose-500/20 rounded-md p-2 min-w-0">
                <span class="text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-500/30 text-rose-300 shrink-0">
                  DELETE
                </span>
                <span class="font-mono font-bold text-rose-400 shrink-0">
                  {formatTrackBadge(item.loser_track)}
                </span>
                <span class="text-[11px] text-muted truncate font-mono" title={item.loser_track.file_path}>
                  {item.loser_track.file_path || 'Unknown Path'}
                </span>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    {:else}
      {#if filteredPendingActions.length === 0}
        <div class="text-muted text-sm italic text-center py-12">No pending actions.</div>
      {/if}
      {#each filteredPendingActions as item}
        <div class="flex justify-between items-center bg-black/20 p-3.5 rounded-global border border-glass-border">
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="text-[10px] uppercase font-bold bg-black/40 px-2 py-0.5 rounded-full text-muted border border-glass-border">
                {item.action_needed}
              </span>
              <span class="text-sm font-bold text-white truncate max-w-[240px]">
                {decodeLabel(item)}
              </span>
            </div>
            <span class="text-xs text-muted">{item.artist || item.originator || 'Unknown'}</span>
          </div>
          <div class="flex gap-2">
            <button
              class="bg-surface-hover text-white text-xs font-bold px-3 py-1 rounded-global hover:scale-95 transition-transform"
              on:click={() => vetoPendingAction(item)}
            >
              Veto
            </button>
            <button
              class="bg-primary text-black text-xs font-bold px-3 py-1 rounded-global hover:scale-95 transition-transform"
              on:click={() => executeNow(item)}
            >
              Execute
            </button>
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<!-- Comparison Modal -->
<DuplicateCompareModal
  item={selectedDuplicate}
  isOpen={isCompareModalOpen}
  on:close={() => (isCompareModalOpen = false)}
  on:resolved={handleModalResolved}
/>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
  }
</style>
