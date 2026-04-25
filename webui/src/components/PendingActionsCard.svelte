<script>
  import { onMount, onDestroy } from 'svelte';
  
  let pendingActions = [];
  let pollingHandle = null;

  async function fetchPendingActions() {
    try {
      const res = await fetch('/api/manager/queue/actions');
      if (res.ok) {
        const data = await res.json();
        pendingActions = data.queue || [];
      }
    } catch (e) { console.error(e); }
  }

  onMount(() => {
    fetchPendingActions();
    pollingHandle = setInterval(fetchPendingActions, 8000);
  });

  onDestroy(() => {
    if (pollingHandle) clearInterval(pollingHandle);
  });
</script>

<div class="flex flex-col h-full min-h-[300px]">
    <div class="flex items-center gap-2 mb-4">
        <div class="w-2 h-2 rounded-full bg-[#3b82f6]"></div>
        <h3 class="text-sm font-bold text-white tracking-tight">Pending Actions <span class="text-muted font-normal">({pendingActions.length})</span></h3>
    </div>

    {#if pendingActions.length === 0}
        <div class="flex-1 flex items-center justify-center bg-[#0d1014] rounded-lg border border-[rgba(255,255,255,0.03)] p-4">
            <span class="text-sm text-muted">No staged lifecycle actions.</span>
        </div>
    {:else}
        <div class="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-2">
            {#each pendingActions as item}
                <div class="p-3 bg-black/20 rounded border border-glass-border">
                    <span class="text-sm text-white">{item.title || item.sync_id}</span>
                </div>
            {/each}
        </div>
    {/if}
</div>
