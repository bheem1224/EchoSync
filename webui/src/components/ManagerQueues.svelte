<script>
  import { onMount, onDestroy } from 'svelte';
  
  let duplicates = [];
  let pendingActions = [];
  let activeTab = 'suggestions';
  let searchQuery = '';
  let queueFilterType = 'All';
  let queueFilterOriginator = 'All';
  let pollingHandle = null;

  function decodeLabel(item) {
    return item?.title || item?.sync_id || 'Unknown';
  }

  async function fetchDuplicates() {
    try {
      const res = await fetch('/api/manager/duplicates');
      if (res.ok) {
        const data = await res.json();
        duplicates = data.duplicates || [];
      }
    } catch (e) { console.error(e); }
  }

  async function fetchPendingActions() {
    try {
      const res = await fetch('/api/manager/queue/actions');
      if (res.ok) {
        const data = await res.json();
        pendingActions = data.queue || [];
      }
    } catch (e) { console.error(e); }
  }

  function _matchesSearch(item) {
    if (!searchQuery || !searchQuery.trim()) return true;
    const s = searchQuery.trim().toLowerCase();
    return (item.title && item.title.toLowerCase().includes(s)) || (item.sync_id && item.sync_id.toLowerCase().includes(s));
  }

  $: filteredSuggestions = (duplicates || []).filter(d => (queueFilterType === 'All' || d.type === queueFilterType) && (queueFilterOriginator === 'All' || (d.originator || 'System') === queueFilterOriginator) && _matchesSearch(d));
  $: filteredPendingActions = (pendingActions || []).filter(i => (queueFilterType === 'All' || i.action_needed === queueFilterType || (queueFilterType === 'Upgrade' && i.action_needed === 'UPGRADE_WEEK_END') || (queueFilterType === 'Deletion' && i.action_needed === 'DELETE_MONTH_END')) && (queueFilterOriginator === 'All' || (i.originator || 'System') === queueFilterOriginator) && _matchesSearch(i));

  onMount(() => {
    fetchDuplicates();
    fetchPendingActions();
    pollingHandle = setInterval(() => {
      fetchPendingActions();
      fetchDuplicates();
    }, 8000);
  });

  onDestroy(() => {
    if (pollingHandle) clearInterval(pollingHandle);
  });

  async function vetoPendingAction(item) {
    try {
      await fetch('/api/manager/suggestion-candidates/override', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ sync_id: item.sync_id, field: 'admin_exempt_deletion', value: true }) });
      fetchPendingActions();
    } catch (e) { console.error(e); }
  }

  async function executeNow(item) {
    try {
      if (!item.track_id) { alert('No track id'); return; }
      const endpoint = item.action_needed === 'DELETE_MONTH_END' ? `/api/manager/track/${item.track_id}/force_delete` : `/api/manager/track/${item.track_id}/force_upgrade`;
      await fetch(endpoint, { method: 'POST' });
      fetchPendingActions();
    } catch (e) { console.error(e); }
  }
</script>

<div class="flex flex-col gap-4">
    <div class="flex items-center gap-4 mb-2">
        <input placeholder="Search..." bind:value={searchQuery} class="flex-1 bg-black/20 border border-glass-border rounded-global px-3 py-1.5 text-sm outline-none focus:border-primary text-white" />
        <select bind:value={queueFilterType} class="bg-black/20 border border-glass-border rounded-global px-2 py-1.5 text-sm outline-none text-white">
            <option>All</option><option>Upgrade</option><option>Deletion</option><option>Duplicate Resolution</option>
        </select>
        <select bind:value={queueFilterOriginator} class="bg-black/20 border border-glass-border rounded-global px-2 py-1.5 text-sm outline-none text-white">
            <option>All</option><option>System</option><option>User</option>
        </select>
    </div>

    <div class="flex gap-4 border-b border-glass-border pb-2">
        <button class="text-sm font-semibold transition-colors {activeTab === 'suggestions' ? 'text-primary border-b-2 border-primary -mb-[9px]' : 'text-muted hover:text-white'}" on:click={() => activeTab = 'suggestions'}>Suggestions & Requests</button>
        <button class="text-sm font-semibold transition-colors {activeTab === 'pending' ? 'text-primary border-b-2 border-primary -mb-[9px]' : 'text-muted hover:text-white'}" on:click={() => activeTab = 'pending'}>Pending Actions</button>
    </div>

    <div class="overflow-y-auto max-h-[400px] flex flex-col gap-2 pr-2 custom-scrollbar">
        {#if activeTab === 'suggestions'}
            {#if filteredSuggestions.length === 0}
                <div class="text-muted text-sm italic text-center py-8">No suggestions at this time.</div>
            {/if}
            {#each filteredSuggestions as item}
                <div class="flex justify-between items-center bg-black/20 p-3 rounded-global border border-glass-border">
                    <div class="flex flex-col gap-1">
                        <div class="flex items-center gap-2">
                            <span class="text-[10px] uppercase font-bold bg-black/40 px-2 py-0.5 rounded-full text-muted border border-glass-border">{item.type}</span>
                            <span class="text-sm font-bold text-white truncate max-w-[200px]">{decodeLabel(item)}</span>
                        </div>
                        <span class="text-xs text-muted">{item.originator || 'System'}</span>
                    </div>
                    <div class="flex gap-2">
                        <button class="bg-primary text-black text-xs font-bold px-3 py-1 rounded-global hover:scale-95 transition-transform">Approve</button>
                        <button class="bg-surface-hover text-white text-xs font-bold px-3 py-1 rounded-global hover:scale-95 transition-transform">Reject</button>
                    </div>
                </div>
            {/each}
        {:else}
            {#if filteredPendingActions.length === 0}
                <div class="text-muted text-sm italic text-center py-8">No pending actions.</div>
            {/if}
            {#each filteredPendingActions as item}
                <div class="flex justify-between items-center bg-black/20 p-3 rounded-global border border-glass-border">
                    <div class="flex flex-col gap-1">
                        <div class="flex items-center gap-2">
                            <span class="text-[10px] uppercase font-bold bg-black/40 px-2 py-0.5 rounded-full text-muted border border-glass-border">{item.action_needed}</span>
                            <span class="text-sm font-bold text-white truncate max-w-[200px]">{decodeLabel(item)}</span>
                        </div>
                        <span class="text-xs text-muted">{item.artist || item.originator || 'Unknown'}</span>
                    </div>
                    <div class="flex gap-2">
                        <button class="bg-surface-hover text-white text-xs font-bold px-3 py-1 rounded-global hover:scale-95 transition-transform" on:click={() => vetoPendingAction(item)}>Veto</button>
                        <button class="bg-primary text-black text-xs font-bold px-3 py-1 rounded-global hover:scale-95 transition-transform" on:click={() => executeNow(item)}>Execute</button>
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>

<style>
    .custom-scrollbar::-webkit-scrollbar { width: 6px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
