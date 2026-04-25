<script>
  import { onMount, onDestroy } from 'svelte';
  
  let duplicates = [];
  let pollingHandle = null;

  async function fetchDuplicates() {
    try {
      const res = await fetch('/api/manager/duplicates');
      if (res.ok) {
        const data = await res.json();
        duplicates = data.duplicates || [];
      }
    } catch (e) { console.error(e); }
  }

  onMount(() => {
    fetchDuplicates();
    pollingHandle = setInterval(fetchDuplicates, 8000);
  });

  onDestroy(() => {
    if (pollingHandle) clearInterval(pollingHandle);
  });
</script>

<div class="flex flex-col h-full min-h-[300px]">
    <div class="flex items-center gap-2 mb-4">
        <div class="w-2 h-2 rounded-full bg-[#f97316]"></div>
        <h3 class="text-sm font-bold text-white tracking-tight">Duplicate Resolution <span class="text-muted font-normal">({duplicates.length})</span></h3>
    </div>

    {#if duplicates.length === 0}
        <div class="flex-1 flex items-center justify-center bg-[#0d1014] rounded-lg border border-[rgba(255,255,255,0.03)] p-4">
            <span class="text-sm text-muted">No conflicts found.</span>
        </div>
    {:else}
        <div class="flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-2">
            {#each duplicates as item}
                <div class="p-3 bg-black/20 rounded border border-glass-border">
                    <span class="text-sm text-white">{item.title || item.sync_id}</span>
                </div>
            {/each}
        </div>
    {/if}
</div>
