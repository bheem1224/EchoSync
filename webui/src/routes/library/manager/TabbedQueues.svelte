<script>
  import { onMount, onDestroy } from 'svelte';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';
  import { flip } from 'svelte/animate';

  // ── State ──────────────────────────────────────────────────────────────
  let activeTab = $state('suggestions');   // 'suggestions' | 'pending'
  let loading    = $state({ suggestions: true, pending: true });
  let data       = $state({ suggestions: [], pending: [] });
  let refreshInterval;

  // ── Lifecycle ──────────────────────────────────────────────────────────
  onMount(async () => {
    await fetchAll();
    refreshInterval = setInterval(fetchAll, 10000);
  });

  onDestroy(() => { if (refreshInterval) clearInterval(refreshInterval); });

  // ── Data fetching ──────────────────────────────────────────────────────
  async function fetchAll() {
    await Promise.all([fetchSuggestions(), fetchPendingActions()]);
  }

  async function fetchSuggestions() {
    try {
      const res = await apiClient.get('/manager/queue/suggestions');
      data.suggestions = res.data.suggestions || [];
    } catch (e) { console.error(e); }
    loading.suggestions = false;
  }

  async function fetchPendingActions() {
    try {
      const res = await apiClient.get('/manager/queue/actions');
      data.pending = res.data.queue || [];
    } catch (e) { console.error(e); }
    loading.pending = false;
  }

  // ── Actions ────────────────────────────────────────────────────────────
  async function handleVeto(sync_id, title) {
    try {
      await apiClient.post('/manager/veto', { sync_id });
      feedback.addToast(`Vetoed: ${title || sync_id}`, 'success');
      data.suggestions = data.suggestions.filter(s => s.sync_id !== sync_id);
      data.pending     = data.pending.filter(p => p.sync_id !== sync_id);
    } catch (e) {
      feedback.addToast('Veto failed', 'error');
    }
  }

  async function handleExecute(sync_id, title) {
    try {
      await apiClient.post('/manager/execute', { sync_id });
      feedback.addToast(`Executing: ${title || sync_id}`, 'success');
      data.pending = data.pending.filter(p => p.sync_id !== sync_id);
    } catch (e) {
      feedback.addToast('Execute failed', 'error');
    }
  }

  async function handleApproveSuggestion(sync_id, title) {
    // Move to pending actions by flagging a lifecycle action via override
    try {
      await apiClient.post('/manager/suggestion-candidates/override', {
        sync_id,
        field: 'status',
        value: 'accepted',
      });
      feedback.addToast(`Approved: ${title || sync_id}`, 'success');
      data.suggestions = data.suggestions.filter(s => s.sync_id !== sync_id);
    } catch (e) {
      feedback.addToast('Approval failed', 'error');
    }
  }

  // ── UI helpers ─────────────────────────────────────────────────────────
  const INTENT_COLORS = {
    USER_UPGRADE_REQUEST:      'bg-blue-500/20 text-blue-300 border-blue-500/30',
    USER_DELETE_REQUEST:       'bg-rose-500/20 text-rose-300 border-rose-500/30',
    SYSTEM_UPGRADE_SUGGESTION: 'bg-violet-500/20 text-violet-300 border-violet-500/30',
    SYSTEM_DELETE_SUGGESTION:  'bg-orange-500/20 text-orange-300 border-orange-500/30',
    HYGIENE_DUPLICATION:       'bg-amber-500/20 text-amber-300 border-amber-500/30',
    HYGIENE_QUALITY_UPGRADE:   'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  };

  const ACTION_COLORS = {
    DELETE_MONTH_END: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    UPGRADE_WEEK_END: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  };

  function intentBadgeClass(item) {
    const key = item.intent_type || item.type || item.action_needed || '';
    return INTENT_COLORS[key] || 'bg-primary/20 text-primary border-primary/30';
  }

  function intentLabel(item) {
    const key = item.intent_type || item.type || item.action_needed || 'SUGGESTION';
    return key.replace(/_/g, ' ');
  }

  function actionBadgeClass(action) {
    return ACTION_COLORS[action] || 'bg-muted/20 text-muted border-muted/30';
  }
</script>

<div class="flex flex-col h-full min-h-0">
  <!-- ── Tab Header ──────────────────────────────────────────────────── -->
  <div class="flex gap-8 border-b border-glass-border mb-6 flex-shrink-0">
    <!-- Suggestions -->
    <button
      id="tab-suggestions"
      class="pb-4 text-sm font-bold tracking-tight transition-all relative {activeTab === 'suggestions' ? 'text-primary' : 'text-muted hover:text-white'}"
      on:click={() => activeTab = 'suggestions'}
    >
      Suggestions
      {#if data.suggestions.length > 0}
        <span class="ml-2 px-1.5 py-0.5 rounded-full bg-primary/20 text-[10px] text-primary">{data.suggestions.length}</span>
      {/if}
      {#if activeTab === 'suggestions'}
        <div class="absolute bottom-0 left-0 w-full h-0.5 bg-primary rounded-full"></div>
      {/if}
    </button>

    <!-- Pending Actions -->
    <button
      id="tab-pending"
      class="pb-4 text-sm font-bold tracking-tight transition-all relative {activeTab === 'pending' ? 'text-primary' : 'text-muted hover:text-white'}"
      on:click={() => activeTab = 'pending'}
    >
      Pending Actions
      {#if data.pending.length > 0}
        <span class="ml-2 px-1.5 py-0.5 rounded-full bg-rose-500/20 text-[10px] text-rose-400">{data.pending.length}</span>
      {/if}
      {#if activeTab === 'pending'}
        <div class="absolute bottom-0 left-0 w-full h-0.5 bg-primary rounded-full"></div>
      {/if}
    </button>
  </div>

  <!-- ── Content Area ────────────────────────────────────────────────── -->
  <div class="flex-grow min-h-0 overflow-y-auto custom-scrollbar pr-2">

    <!-- Suggestions Tab -->
    {#if activeTab === 'suggestions'}
      {#if loading.suggestions}
        <div class="py-16 text-center text-muted italic">Loading suggestions…</div>
      {:else if data.suggestions.length === 0}
        <div class="py-16 flex flex-col items-center gap-3 text-muted">
          <svg class="w-12 h-12 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <p class="text-sm">No pending suggestions. The library looks clean.</p>
        </div>
      {:else}
        <div class="flex flex-col gap-3">
          {#each data.suggestions as item (item.sync_id)}
            <div
              animate:flip="{{ duration: 200 }}"
              class="flex items-center justify-between p-4 bg-surface/40 border border-glass-border rounded-2xl hover:bg-surface/60 transition-colors group"
            >
              <div class="flex flex-col gap-1.5 min-w-0 mr-4">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-[10px] uppercase font-black px-2 py-0.5 rounded-md border {intentBadgeClass(item)}">
                    {intentLabel(item)}
                  </span>
                  <span class="text-sm font-bold text-white truncate max-w-[360px]">{item.title || 'Unknown'}</span>
                </div>
                <div class="text-[11px] text-muted flex items-center gap-2">
                  <span>{item.originator || 'Consensus Engine'}</span>
                  {#if item.artist}
                    <span class="w-1 h-1 rounded-full bg-muted/40"></span>
                    <span>{item.artist}</span>
                  {/if}
                </div>
              </div>

              <div class="flex gap-2 flex-shrink-0">
                <button
                  class="px-4 py-2 bg-primary text-black text-xs font-black rounded-lg hover:scale-105 active:scale-95 transition-all"
                  on:click={() => handleApproveSuggestion(item.sync_id, item.title)}
                >
                  APPROVE
                </button>
                <button
                  class="px-4 py-2 bg-surface-hover text-white text-xs font-bold rounded-lg hover:bg-rose-500/20 hover:text-rose-400 transition-all"
                  on:click={() => handleVeto(item.sync_id, item.title)}
                >
                  VETO
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}

    <!-- Pending Actions Tab -->
    {:else if activeTab === 'pending'}
      {#if loading.pending}
        <div class="py-16 text-center text-muted italic">Loading pending actions…</div>
      {:else if data.pending.length === 0}
        <div class="py-16 flex flex-col items-center gap-3 text-muted">
          <svg class="w-12 h-12 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 13l4 4L19 7"/>
          </svg>
          <p class="text-sm">No pending lifecycle actions. Everything is up to date.</p>
        </div>
      {:else}
        <div class="flex flex-col gap-3">
          {#each data.pending as item (item.sync_id)}
            <div
              animate:flip="{{ duration: 200 }}"
              class="flex items-center justify-between p-4 bg-surface/40 border border-glass-border rounded-2xl hover:bg-surface/60 transition-colors"
            >
              <div class="flex flex-col gap-1.5 min-w-0 mr-4">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-[10px] uppercase font-black px-2 py-0.5 rounded-md border {actionBadgeClass(item.action_needed)}">
                    {(item.action_needed || 'PENDING').replace(/_/g, ' ')}
                  </span>
                  <span class="text-sm font-bold text-white truncate max-w-[320px]">{item.title || item.sync_id}</span>
                </div>
                <div class="text-[11px] text-muted flex items-center gap-2">
                  {#if item.artist}<span>{item.artist}</span><span class="w-1 h-1 rounded-full bg-muted/40"></span>{/if}
                  <span class="text-primary/80">
                    {item.days_in_queue != null ? `${item.days_in_queue}d in queue` : 'Queued'}
                  </span>
                  {#if item.admin_exempt_deletion}
                    <span class="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] uppercase font-bold border border-amber-500/30">Exempt</span>
                  {/if}
                </div>
              </div>

              <div class="flex gap-2 flex-shrink-0">
                <button
                  class="px-4 py-2 bg-emerald-500/20 text-emerald-300 text-xs font-black rounded-lg hover:bg-emerald-500/40 active:scale-95 transition-all border border-emerald-500/30"
                  on:click={() => handleExecute(item.sync_id, item.title)}
                >
                  EXECUTE NOW
                </button>
                <button
                  class="px-4 py-2 bg-surface-hover text-muted text-xs font-bold rounded-lg hover:bg-rose-500/20 hover:text-rose-400 transition-all"
                  on:click={() => handleVeto(item.sync_id, item.title)}
                >
                  VETO
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 10px; }
</style>
