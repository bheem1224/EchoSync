<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { dndzone } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';
  import apiClient from '../../../api/client';
  import { feedback } from '../../../stores/feedback';

  const dispatch = createEventDispatcher();

  // ── State ──────────────────────────────────────────────────────────────
  let musicAccounts = [];   // Unmapped source pills
  let mediaUsers    = [];   // Drop-zone targets
  let loading       = true;
  const flipDurationMs = 200;

  // ── Data loading ───────────────────────────────────────────────────────
  onMount(loadAccounts);

  async function loadAccounts() {
    loading = true;
    try {
      const res = await apiClient.get('/system/accounts');
      const d = res.data;

      // Build a set of already-linked account ids
      const linkedIds = new Set();
      d.media_users.forEach(u => u.linked_account_ids.forEach(id => linkedIds.add(id)));

      musicAccounts = d.music_accounts
        .filter(a => !linkedIds.has(a.id))
        .map(a => ({ ...a, id: String(a.id) }));

      mediaUsers = d.media_users.map(u => ({
        ...u,
        linked_items: d.music_accounts
          .filter(a => u.linked_account_ids.includes(a.id))
          .map(a => ({ ...a, id: String(a.id) })),
      }));
    } catch (e) {
      console.error(e);
      feedback.addToast('Failed to load accounts', 'error');
    } finally {
      loading = false;
    }
  }

  // ── DnD – pool ─────────────────────────────────────────────────────────
  function handleConsiderPool(e) {
    musicAccounts = e.detail.items;
  }

  function handleFinalizePool(e) {
    musicAccounts = e.detail.items;
    // No API call needed when returning to pool
  }

  // ── DnD – user drop zones ──────────────────────────────────────────────
  function handleConsiderUser(userId, e) {
    const idx = mediaUsers.findIndex(u => u.id === userId);
    if (idx === -1) return;
    mediaUsers[idx].linked_items = e.detail.items;
    mediaUsers = [...mediaUsers];
  }

  async function handleFinalizeUser(userId, e) {
    const idx = mediaUsers.findIndex(u => u.id === userId);
    if (idx === -1) return;
    mediaUsers[idx].linked_items = e.detail.items;
    mediaUsers = [...mediaUsers];

    try {
      const account_ids = mediaUsers[idx].linked_items.map(item => parseInt(item.id, 10));
      await apiClient.post('/system/accounts/map', { user_id: userId, account_ids });
      feedback.addToast(`Mapping saved for ${mediaUsers[idx].name}`, 'success');
    } catch (err) {
      console.error(err);
      feedback.addToast('Failed to save mapping', 'error');
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  function serviceColor(service = '') {
    switch (service.toLowerCase()) {
      case 'spotify': return '#1DB954';
      case 'tidal':   return '#00E5FF';
      default:        return '#8B5CF6';
    }
  }

  function serviceIcon(service = '') {
    switch (service.toLowerCase()) {
      case 'spotify': return '♫';
      case 'tidal':   return '◈';
      default:        return '♪';
    }
  }

  function initials(name = '') {
    return name.trim().charAt(0).toUpperCase();
  }
</script>

<!-- ── Backdrop ─────────────────────────────────────────────────────────── -->
<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
<div
  class="fixed inset-0 z-50 flex items-center justify-center p-4"
  on:click|self={() => dispatch('close')}
  style="background: rgba(0,0,0,0.75); backdrop-filter: blur(8px);"
>
  <!-- ── Modal Shell ──────────────────────────────────────────────────── -->
  <div class="relative w-full max-w-5xl max-h-[90vh] bg-[#0a0a0f] border border-glass-border rounded-[2rem] shadow-2xl flex flex-col overflow-hidden modal-enter">

    <!-- Header -->
    <div class="flex items-center justify-between px-8 py-6 border-b border-glass-border flex-shrink-0">
      <div class="flex flex-col gap-1">
        <div class="text-[10px] uppercase font-black tracking-[0.25em] text-primary">Account Builder</div>
        <h2 class="text-xl font-black text-white flex items-center gap-3">
          Managed Account Mapping
          <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
        </h2>
        <p class="text-xs text-muted mt-1">Drag music service accounts onto media server users to fuse listening histories.</p>
      </div>
      <button
        id="close-account-builder-btn"
        class="w-9 h-9 rounded-full bg-surface/60 border border-glass-border flex items-center justify-center text-muted hover:text-white hover:border-primary/50 transition-all"
        on:click={() => dispatch('close')}
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <!-- Body -->
    {#if loading}
      <div class="flex-grow flex items-center justify-center py-24 text-muted italic">
        Loading accounts…
      </div>
    {:else}
      <div class="flex-grow min-h-0 overflow-y-auto custom-scrollbar">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-0 h-full">

          <!-- ── LEFT: Unmapped Music Accounts ──────────────────────── -->
          <div class="flex flex-col gap-4 p-8 border-r border-glass-border">
            <div class="flex-shrink-0">
              <h3 class="text-xs font-black uppercase tracking-widest text-secondary/80 flex items-center gap-2 mb-1">
                <span class="w-1.5 h-1.5 rounded-full bg-secondary/60"></span>
                Unmapped Music Accounts
              </h3>
              <p class="text-[11px] text-muted">Grab a pill and drop it onto a user →</p>
            </div>

            <!-- DnD Pool -->
            <div
              class="flex flex-wrap content-start gap-3 p-4 bg-black/30 border border-dashed border-white/10 rounded-2xl min-h-[180px] transition-colors"
              use:dndzone="{{ items: musicAccounts, flipDurationMs, dropTargetStyle: {outline: '2px dashed var(--color-primary)', borderRadius: '16px'} }}"
              on:consider={handleConsiderPool}
              on:finalize={handleFinalizePool}
            >
              {#each musicAccounts as acc (acc.id)}
                <div
                  animate:flip="{{ duration: flipDurationMs }}"
                  class="account-pill cursor-grab active:cursor-grabbing"
                  style="--service-color: {serviceColor(acc.service)}"
                >
                  <span class="pill-icon">{serviceIcon(acc.service)}</span>
                  <div class="pill-text">
                    <span class="pill-name">{acc.name}</span>
                    <span class="pill-service">{acc.service}</span>
                  </div>
                </div>
              {/each}

              {#if musicAccounts.length === 0}
                <div class="m-auto text-[11px] text-muted italic pointer-events-none flex flex-col items-center gap-2">
                  <svg class="w-8 h-8 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  All accounts assigned
                </div>
              {/if}
            </div>
          </div>

          <!-- ── RIGHT: Media Server Users (Drop Zones) ──────────────── -->
          <div class="flex flex-col gap-5 p-8">
            <div class="flex-shrink-0">
              <h3 class="text-xs font-black uppercase tracking-widest text-primary/80 flex items-center gap-2 mb-1">
                <span class="w-1.5 h-1.5 rounded-full bg-primary/60"></span>
                Media Server Users
              </h3>
              <p class="text-[11px] text-muted">Drop music accounts here to link them.</p>
            </div>

            {#each mediaUsers as user (user.id)}
              <div class="user-card">
                <!-- User header -->
                <div class="flex items-center gap-3 mb-3">
                  <div class="user-avatar">
                    {initials(user.name)}
                  </div>
                  <div class="flex flex-col">
                    <span class="text-sm font-bold text-white">{user.name}</span>
                    <span class="text-[10px] text-muted uppercase tracking-tighter">
                      {user.is_admin ? 'Server Admin' : 'Managed User'}
                    </span>
                  </div>
                </div>

                <!-- Drop Zone -->
                <div
                  class="flex flex-wrap gap-2 min-h-[52px] p-3 bg-black/20 rounded-xl border border-dashed border-white/8 transition-colors"
                  use:dndzone="{{ items: user.linked_items, flipDurationMs, dropTargetStyle: {outline: '2px dashed var(--color-primary)', borderRadius: '12px'} }}"
                  on:consider={(e) => handleConsiderUser(user.id, e)}
                  on:finalize={(e) => handleFinalizeUser(user.id, e)}
                >
                  {#each user.linked_items as acc (acc.id)}
                    <div
                      animate:flip="{{ duration: flipDurationMs }}"
                      class="account-pill account-pill--sm cursor-grab active:cursor-grabbing"
                      style="--service-color: {serviceColor(acc.service)}"
                    >
                      <span class="pill-icon">{serviceIcon(acc.service)}</span>
                      <span class="pill-name">{acc.name}</span>
                    </div>
                  {/each}

                  {#if user.linked_items.length === 0}
                    <span class="text-[10px] text-muted italic m-auto pointer-events-none">Drop accounts here</span>
                  {/if}
                </div>
              </div>
            {/each}

            {#if mediaUsers.length === 0}
              <div class="flex-grow flex items-center justify-center text-muted text-sm italic">
                No media server users found. Check your Plex/Jellyfin connection.
              </div>
            {/if}
          </div>

        </div>
      </div>
    {/if}

    <!-- Footer -->
    <div class="flex items-center justify-between px-8 py-4 border-t border-glass-border flex-shrink-0 bg-black/20">
      <p class="text-[11px] text-muted">Changes are saved automatically when you drop an account.</p>
      <button
        class="px-5 py-2 rounded-xl bg-surface/60 border border-glass-border text-sm font-bold text-white hover:border-primary/50 transition-all"
        on:click={() => dispatch('close')}
      >
        Done
      </button>
    </div>
  </div>
</div>

<style>
  /* ── Modal entrance animation ─────────────────────────────────────── */
  .modal-enter {
    animation: modalIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) both;
  }
  @keyframes modalIn {
    from { opacity: 0; transform: scale(0.96) translateY(12px); }
    to   { opacity: 1; transform: scale(1) translateY(0); }
  }

  /* ── Account Pills ────────────────────────────────────────────────── */
  .account-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 999px;
    transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s;
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
  }
  .account-pill:hover {
    border-color: var(--service-color, var(--color-primary));
    transform: scale(1.04);
    box-shadow: 0 4px 20px color-mix(in srgb, var(--service-color, #1DB954) 25%, transparent);
  }
  .account-pill--sm { padding: 5px 10px; gap: 6px; }

  .pill-icon {
    font-size: 14px;
    color: var(--service-color, var(--color-primary));
    line-height: 1;
  }
  .pill-text  { display: flex; flex-direction: column; gap: 1px; }
  .pill-name  { font-size: 11px; font-weight: 700; color: #fff; white-space: nowrap; }
  .pill-service { font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255,255,255,0.4); }

  /* ── User Cards ───────────────────────────────────────────────────── */
  .user-card {
    padding: 16px;
    background: rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 18px;
    transition: border-color 0.2s, background 0.2s;
  }
  .user-card:hover { background: rgba(0,0,0,0.35); border-color: rgba(255,255,255,0.1); }

  .user-avatar {
    width: 34px; height: 34px;
    border-radius: 50%;
    background: rgba(29,185,84,0.15);
    border: 1px solid rgba(29,185,84,0.3);
    color: var(--color-primary);
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 900;
    flex-shrink: 0;
  }

  /* ── Scrollbar ────────────────────────────────────────────────────── */
  .custom-scrollbar::-webkit-scrollbar { width: 4px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 10px; }
</style>
