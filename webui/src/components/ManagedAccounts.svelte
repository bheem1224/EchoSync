<script>
  import { onMount } from 'svelte';
  
  let accounts = [];

  onMount(() => {
    // Mock for now, would fetch from /api/manager/accounts or similar
    accounts = [];
  });
</script>

<div class="flex flex-col">
    <div class="flex justify-between items-center mb-4">
        <h3 class="text-base font-bold text-white tracking-tight">Managed Accounts (plex)</h3>
        <div class="flex gap-2">
            <button class="bg-primary/10 border border-primary/20 text-primary px-3 py-1 text-[11px] font-bold rounded-md hover:bg-primary/20 transition-colors">Sync Managed Users</button>
            <button class="bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.1)] text-white px-3 py-1 text-[11px] font-bold rounded-md hover:bg-[rgba(255,255,255,0.1)] transition-colors">Refresh Accounts</button>
        </div>
    </div>

    {#if accounts.length === 0}
        <div class="flex items-center justify-center py-8 text-muted text-sm italic">
            No managed accounts found for plex.
        </div>
    {:else}
        <div class="flex flex-col gap-2">
            {#each accounts as account}
                <div class="flex items-center justify-between p-3 bg-black/20 rounded border border-glass-border">
                    <span class="text-sm font-bold text-white">{account.name}</span>
                </div>
            {/each}
        </div>
    {/if}
</div>
