<script>
  import { dndzone } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';

  export let managedAccounts = [
    { 
      id: 'plex_user_1', 
      account_name: 'bheem', 
      linked_services: [
        { id: 'spot_1', service: 'Spotify', username: 'bheem_real', color: '#1DB954' }
      ] 
    },
    { 
      id: 'plex_user_2', 
      account_name: 'simi', 
      linked_services: [] 
    }
  ];

  export let unassignedServices = [
    { id: 'spot_2', service: 'Spotify', username: 'simi_music', color: '#1DB954' },
    { id: 'slsk_1', service: 'Slskd', username: 'guest_dl', color: '#5b21b6' }
  ];

  const flipDurationMs = 200;

  function handleDndConsiderManaged(accountId, e) {
    const accountIndex = managedAccounts.findIndex(a => a.id === accountId);
    managedAccounts[accountIndex].linked_services = e.detail.items;
    managedAccounts = [...managedAccounts];
  }

  function handleDndFinalizeManaged(accountId, e) {
    const accountIndex = managedAccounts.findIndex(a => a.id === accountId);
    managedAccounts[accountIndex].linked_services = e.detail.items;
    managedAccounts = [...managedAccounts];
  }

  function handleDndConsiderUnassigned(e) {
    unassignedServices = e.detail.items;
  }

  function handleDndFinalizeUnassigned(e) {
    unassignedServices = e.detail.items;
  }
</script>

<div class="flex flex-col h-full w-full text-white">
  <!-- Header -->
  <div class="flex items-center gap-2 mb-6 border-b border-glass-border pb-4">
    <svg class="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
    </svg>
    <h3 class="text-lg font-bold">Managed Accounts</h3>
  </div>

  <div class="flex flex-col gap-4 flex-grow overflow-y-auto custom-scrollbar">
    <!-- Managed Accounts Section -->
    {#each managedAccounts as account (account.id)}
      <div class="flex flex-col gap-3 p-3 bg-black/20 rounded-xl border border-glass-border">
        <div class="flex items-center gap-3 px-1">
          <div class="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-sm uppercase shrink-0">
            {account.account_name.charAt(0)}
          </div>
          <div class="flex flex-col overflow-hidden">
            <span class="text-sm font-bold text-white truncate">{account.account_name}</span>
            {#if account.id === 'plex_user_1'}
              <span class="text-[10px] text-primary uppercase tracking-wider font-semibold truncate">Primary Account</span>
            {:else}
              <span class="text-[10px] text-secondary uppercase tracking-wider font-semibold truncate">Shared Library</span>
            {/if}
          </div>
        </div>

        <!-- Dropzone for this account -->
        <div 
          class="flex flex-wrap gap-2 min-h-[48px] p-2 bg-black/20 rounded-md"
          use:dndzone="{{items: account.linked_services, flipDurationMs}}"
          on:consider={(e) => handleDndConsiderManaged(account.id, e)}
          on:finalize={(e) => handleDndFinalizeManaged(account.id, e)}
        >
          {#each account.linked_services as service (service.id)}
            <div 
              animate:flip="{{duration: flipDurationMs}}"
              class="px-3 py-1.5 text-xs font-bold rounded-full select-none cursor-grab active:cursor-grabbing text-white active:scale-110 md:active:scale-100 transition-transform shadow-md"
              style="background-color: {service.color};"
            >
              {service.service.toUpperCase()}
            </div>
          {/each}
        </div>
      </div>
    {/each}

    <!-- Unassigned Services Pool -->
    <div class="flex flex-col gap-3 mt-4 mb-2">
      <h4 class="text-xs uppercase tracking-wider font-semibold text-secondary px-1">UNASSIGNED SERVICES</h4>
      
      <div 
        class="flex flex-wrap gap-2 min-h-[100px] p-4 bg-surface/50 border border-dashed border-glass-border rounded-lg"
        use:dndzone="{{items: unassignedServices, flipDurationMs}}"
        on:consider={handleDndConsiderUnassigned}
        on:finalize={handleDndFinalizeUnassigned}
      >
        {#each unassignedServices as service (service.id)}
          <div 
            animate:flip="{{duration: flipDurationMs}}"
            class="px-3 py-1.5 text-xs font-bold rounded-full select-none cursor-grab active:cursor-grabbing text-white active:scale-110 md:active:scale-100 transition-transform shadow-md"
            style="background-color: {service.color};"
          >
            {service.service.toUpperCase()}
          </div>
        {/each}
      </div>
    </div>
  </div>
</div>
