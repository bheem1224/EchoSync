<script>
  import { onMount } from 'svelte';
  import { dndzone } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';

  let musicAccounts = []; // Draggable items (Available Music Accounts)
  let mediaUsers = [];   // Drop Zones (Media Server Users)
  let loading = true;

  const flipDurationMs = 200;

  onMount(async () => {
    await loadAccounts();
  });

  async function loadAccounts() {
    try {
      const res = await apiClient.get('/system/accounts');
      const data = res.data;
      
      // Music accounts that are NOT linked to any user go to the "Available" pool
      const linkedIds = new Set();
      data.media_users.forEach(user => {
        user.linked_account_ids.forEach(id => linkedIds.add(id));
      });

      musicAccounts = data.music_accounts
        .filter(acc => !linkedIds.has(acc.id))
        .map(acc => ({ ...acc, id: acc.id.toString() })); // dnd-action needs string IDs or consistent unique IDs

      mediaUsers = data.media_users.map(user => ({
        ...user,
        linked_items: data.music_accounts
          .filter(acc => user.linked_account_ids.includes(acc.id))
          .map(acc => ({ ...acc, id: acc.id.toString() }))
      }));
      
      loading = false;
    } catch (err) {
      console.error('Failed to load accounts for mapping:', err);
      feedback.addToast('Failed to load accounts', 'error');
    }
  }

  // Pool of available accounts
  function handleConsiderPool(e) {
    musicAccounts = e.detail.items;
  }

  async function handleFinalizePool(e) {
    musicAccounts = e.detail.items;
    // When an item is dropped back into the pool, we don't necessarily need an API call 
    // unless we want to clear its mapping immediately.
  }

  // Drop zones for each user
  function handleConsiderUser(userId, e) {
    const idx = mediaUsers.findIndex(u => u.id === userId);
    mediaUsers[idx].linked_items = e.detail.items;
    mediaUsers = [...mediaUsers];
  }

  async function handleFinalizeUser(userId, e) {
    const idx = mediaUsers.findIndex(u => u.id === userId);
    mediaUsers[idx].linked_items = e.detail.items;
    mediaUsers = [...mediaUsers];

    // Save mapping to backend
    try {
      const account_ids = mediaUsers[idx].linked_items.map(item => parseInt(item.id));
      await apiClient.post('/system/accounts/map', {
        user_id: userId,
        account_ids: account_ids
      });
      feedback.addToast(`Updated mapping for ${mediaUsers[idx].name}`, 'success');
    } catch (err) {
      console.error('Failed to save mapping:', err);
      feedback.addToast('Failed to save mapping', 'error');
    }
  }

  function getServiceIcon(service) {
    switch (service.toLowerCase()) {
      case 'spotify': return '';
      case 'tidal': return '';
      case 'slskd': return '󰚝';
      default: return '';
    }
  }
</script>

<aside class="flex flex-col h-full bg-surface/40 backdrop-blur-md border-l border-glass-border p-6 overflow-y-auto custom-scrollbar">
  <div class="mb-8">
    <h2 class="text-xl font-bold text-white flex items-center gap-2">
      <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
      Managed Account Builder
    </h2>
    <p class="text-xs text-muted mt-2">Drag music service accounts into media users to fuse histories.</p>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20 text-muted italic">Loading accounts...</div>
  {:else}
    <!-- Drop Zones: Media Server Users -->
    <div class="flex flex-col gap-6 mb-10">
      <h3 class="text-xs font-bold uppercase tracking-widest text-primary/80 px-1">Media Server Users</h3>
      {#each mediaUsers as user (user.id)}
        <div class="flex flex-col gap-3 p-4 bg-black/30 rounded-2xl border border-glass-border transition-all hover:bg-black/40">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold text-xs uppercase border border-primary/30">
                {user.name.charAt(0)}
              </div>
              <div class="flex flex-col">
                <span class="text-sm font-bold text-white">{user.name}</span>
                <span class="text-[10px] text-muted uppercase tracking-tighter">{user.is_admin ? 'Server Admin' : 'Managed User'}</span>
              </div>
            </div>
          </div>

          <!-- Drop Zone -->
          <div 
            class="flex flex-wrap gap-2 min-h-[50px] p-3 bg-black/20 rounded-xl border border-dashed border-white/5 transition-colors"
            use:dndzone="{{items: user.linked_items, flipDurationMs, dropTargetStyle: {outline: '2px dashed var(--color-primary)', borderRadius: '12px'}}}"
            on:consider={(e) => handleConsiderUser(user.id, e)}
            on:finalize={(e) => handleFinalizeUser(user.id, e)}
          >
            {#each user.linked_items as acc (acc.id)}
              <div 
                animate:flip="{{duration: flipDurationMs}}"
                class="px-3 py-1.5 bg-surface-hover border border-glass-border rounded-full flex items-center gap-2 cursor-grab active:cursor-grabbing shadow-lg hover:border-primary/50 transition-colors"
              >
                <span class="text-xs" style="color: {acc.color}">{getServiceIcon(acc.service)}</span>
                <span class="text-[11px] font-bold text-white whitespace-nowrap">{acc.name}</span>
              </div>
            {/each}
            {#if user.linked_items.length === 0}
              <div class="text-[10px] text-muted italic m-auto pointer-events-none">Drop music accounts here</div>
            {/if}
          </div>
        </div>
      {/each}
    </div>

    <!-- Source Pool: Available Music Accounts -->
    <div class="flex flex-col gap-4">
      <h3 class="text-xs font-bold uppercase tracking-widest text-secondary/80 px-1">Available Music Accounts</h3>
      <div 
        class="flex flex-wrap gap-2 p-4 bg-surface/20 border border-dashed border-glass-border rounded-2xl min-h-[120px]"
        use:dndzone="{{items: musicAccounts, flipDurationMs}}"
        on:consider={handleConsiderPool}
        on:finalize={handleFinalizePool}
      >
        {#each musicAccounts as acc (acc.id)}
          <div 
            animate:flip="{{duration: flipDurationMs}}"
            class="px-4 py-2 bg-black/40 border border-glass-border rounded-full flex items-center gap-3 cursor-grab active:cursor-grabbing shadow-xl hover:scale-105 transition-transform"
          >
            <div class="w-2 h-2 rounded-full" style="background-color: {acc.color}"></div>
            <div class="flex flex-col">
              <span class="text-xs font-bold text-white leading-tight">{acc.name}</span>
              <span class="text-[9px] text-muted uppercase tracking-tighter">{acc.service}</span>
            </div>
          </div>
        {/each}
        {#if musicAccounts.length === 0}
          <div class="text-[10px] text-muted italic m-auto pointer-events-none">All accounts assigned</div>
        {/if}
      </div>
    </div>
  {/if}
</aside>

<style>
  @font-face {
    font-family: 'FontAwesome';
    src: url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2') format('woff2');
  }
  .custom-scrollbar::-webkit-scrollbar { width: 4px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
</style>
