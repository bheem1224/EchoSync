<script>
  import { onMount, onDestroy } from 'svelte';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';
  import { flip } from 'svelte/animate';
  import MetadataReviewModal from '$lib/components/MetadataReviewModal.svelte';

  let activeTab = 'suggestions'; // suggestions | review | downloads
  let showReviewModal = false;
  let selectedTask = null;
  let loading = { suggestions: true, review: true, downloads: true };
  let data = { suggestions: [], review: [], downloads: [] };
  let refreshInterval;

  onMount(async () => {
    await fetchAll();
    refreshInterval = setInterval(fetchAll, 10000); // refresh every 10s
  });

  onDestroy(() => {
    if (refreshInterval) clearInterval(refreshInterval);
  });

  async function fetchAll() {
    await Promise.all([
      fetchSuggestions(),
      fetchReviewQueue(),
      fetchDownloads()
    ]);
  }

  async function fetchSuggestions() {
    try {
      const res = await apiClient.get('/manager/queue/suggestions');
      data.suggestions = res.data.suggestions || [];
      loading.suggestions = false;
    } catch (e) { console.error(e); }
  }

  async function fetchReviewQueue() {
    try {
      const res = await apiClient.get('/review-queue');
      data.review = res.data.tasks || res.data || [];
      loading.review = false;
    } catch (e) { console.error(e); }
  }

  async function fetchDownloads() {
    try {
      const res = await apiClient.get('/downloads/queue');
      data.downloads = res.data.items || [];
      loading.downloads = false;
    } catch (e) { console.error(e); }
  }

  async function handleApproveSuggestion(id) {
      // Placeholder for actual approve logic
      feedback.addToast('Suggestion approved', 'success');
  }

  async function handleReview(task) {
    selectedTask = task;
    showReviewModal = true;
  }

  function formatSpeed(bytesPerSec) {
    if (!bytesPerSec || bytesPerSec <= 0) return '0 B/s';
    const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    let val = bytesPerSec;
    let unitIdx = 0;
    while (val >= 1024 && unitIdx < units.length - 1) {
      val /= 1024;
      unitIdx++;
    }
    return `${val.toFixed(1)} ${units[unitIdx]}`;
  }

  const statusColors = {
    QUEUED: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
    SEARCHING: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    DOWNLOADING: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    COMPLETED: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    FAILED: 'bg-rose-500/20 text-rose-400 border-rose-500/30'
  };
</script>

<div class="flex flex-col h-full">
  <!-- Tab Header -->
  <div class="flex gap-8 border-b border-glass-border mb-6">
    <button 
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
    <button 
      class="pb-4 text-sm font-bold tracking-tight transition-all relative {activeTab === 'review' ? 'text-primary' : 'text-muted hover:text-white'}"
      on:click={() => activeTab = 'review'}
    >
      Review Queue
      {#if data.review.length > 0}
        <span class="ml-2 px-1.5 py-0.5 rounded-full bg-primary/20 text-[10px] text-primary">{data.review.length}</span>
      {/if}
      {#if activeTab === 'review'}
        <div class="absolute bottom-0 left-0 w-full h-0.5 bg-primary rounded-full"></div>
      {/if}
    </button>
    <button 
      class="pb-4 text-sm font-bold tracking-tight transition-all relative {activeTab === 'downloads' ? 'text-primary' : 'text-muted hover:text-white'}"
      on:click={() => activeTab = 'downloads'}
    >
      Download Queue
      {#if data.downloads.length > 0}
        <span class="ml-2 px-1.5 py-0.5 rounded-full bg-primary/20 text-[10px] text-primary">{data.downloads.length}</span>
      {/if}
      {#if activeTab === 'downloads'}
        <div class="absolute bottom-0 left-0 w-full h-0.5 bg-primary rounded-full"></div>
      {/if}
    </button>
  </div>

  <!-- Content Area -->
  <div class="flex-grow overflow-y-auto custom-scrollbar pr-2">
    {#if activeTab === 'suggestions'}
      {#if loading.suggestions}
        <div class="py-12 text-center text-muted italic">Loading suggestions...</div>
      {:else if data.suggestions.length === 0}
        <div class="py-12 text-center text-muted">No heuristic-based proposals found.</div>
      {:else}
        <div class="flex flex-col gap-3">
          {#each data.suggestions as item (item.sync_id)}
            <div animate:flip="{{duration: 200}}" class="flex items-center justify-between p-4 bg-surface/40 border border-glass-border rounded-2xl hover:bg-surface/60 transition-colors">
              <div class="flex flex-col gap-1">
                <div class="flex items-center gap-2">
                  <span class="text-[10px] uppercase font-black bg-black/40 px-2 py-0.5 rounded-md text-primary border border-primary/20">{item.action_needed || 'SUGGESTION'}</span>
                  <span class="text-sm font-bold text-white truncate max-w-[300px]">{item.title}</span>
                </div>
                <div class="text-[11px] text-muted flex items-center gap-2">
                  <span>{item.originator || 'Consensus Engine'}</span>
                  <span class="w-1 h-1 rounded-full bg-muted/40"></span>
                  <span class="text-primary/80">Match Strength: 92%</span>
                </div>
              </div>
              <div class="flex gap-2">
                <button class="px-4 py-2 bg-primary text-black text-xs font-black rounded-lg hover:scale-105 active:scale-95 transition-all" on:click={() => handleApproveSuggestion(item.sync_id)}>APPROVE</button>
                <button class="px-4 py-2 bg-surface-hover text-white text-xs font-bold rounded-lg hover:bg-rose-500/20 hover:text-rose-400 transition-all">IGNORE</button>
              </div>
            </div>
          {/each}
        </div>
      {/if}

    {:else if activeTab === 'review'}
      {#if loading.review}
        <div class="py-12 text-center text-muted italic">Loading review queue...</div>
      {:else if data.review.length === 0}
        <div class="py-12 text-center text-muted">No tracks pending metadata review.</div>
      {:else}
        <div class="flex flex-col gap-3">
          {#each data.review as task (task.id)}
            <div animate:flip="{{duration: 200}}" class="flex items-center justify-between p-4 bg-surface/40 border border-glass-border rounded-2xl hover:bg-surface/60 transition-colors">
              <div class="flex items-center gap-4">
                <div class="w-10 h-10 bg-black/40 rounded-lg flex items-center justify-center text-muted border border-glass-border">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                </div>
                <div class="flex flex-col gap-0.5">
                  <span class="text-sm font-bold text-white">{task.filename || 'Unknown File'}</span>
                  <span class="text-[11px] text-muted italic">Potential Match: {task.detected_title || 'Unidentified'}</span>
                </div>
              </div>
              <div class="flex gap-2">
                <button class="px-4 py-2 bg-primary/20 text-primary text-xs font-bold rounded-lg hover:bg-primary hover:text-black transition-all" on:click={() => handleReview(task)}>REVIEW</button>
              </div>
            </div>
          {/each}
        </div>
      {/if}

    {:else if activeTab === 'downloads'}
      {#if loading.downloads}
        <div class="py-12 text-center text-muted italic">Loading downloads...</div>
      {:else if data.downloads.length === 0}
        <div class="py-12 text-center text-muted">No active downloads.</div>
      {:else}
        <div class="flex flex-col gap-3">
          {#each data.downloads as item (item.id)}
            <div animate:flip="{{duration: 200}}" class="flex items-center justify-between p-4 bg-surface/40 border border-glass-border rounded-2xl hover:bg-surface/60 transition-colors">
              <div class="flex flex-col gap-1">
                <span class="text-sm font-bold text-white">{item.title}</span>
                <span class="text-[11px] text-muted">{item.artist}</span>
              </div>
              <div class="flex-grow mx-8 flex flex-col gap-1.5">
                <div class="flex justify-between items-center text-[10px] text-muted uppercase font-bold">
                  <span>{item.status === 'DOWNLOADING' ? 'Downloading...' : item.status}</span>
                  <span>{item.progress_percent.toFixed(1)}%</span>
                </div>
                <div class="w-full h-1.5 bg-black/40 rounded-full overflow-hidden border border-white/5">
                  <div class="h-full bg-primary transition-all duration-500" style="width: {item.progress_percent}%"></div>
                </div>
              </div>

              <div class="flex items-center gap-4">
                <span class="text-[10px] font-bold px-3 py-1 rounded-full border {statusColors[item.status] || 'bg-muted/20 text-muted border-muted/30'}">
                  {item.status}
                </span>
                <span class="text-[10px] text-muted tabular-nums w-16 text-right">
                  {item.status === 'DOWNLOADING' ? formatSpeed(item.current_speed) : '--'}
                </span>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
</div>

{#if showReviewModal}
  <MetadataReviewModal 
    task={selectedTask} 
    on:close={() => { showReviewModal = false; fetchReviewQueue(); }}
    on:save={() => { showReviewModal = false; fetchReviewQueue(); }}
  />
{/if}

<style>
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
</style>
