<script>
  import { onMount, onDestroy } from 'svelte';
  import { decodeSyncId } from '../../../lib/utils';

  // Manager settings persisted via backend
  let settings = {
    enabled: true,
    delete_threshold: 1,
    upgrade_threshold: 2,
    auto_delete: false,
    auto_upgrade: false,
    upgrade_quality_profile_id: '',
    auto_delete_low_quality_duplicates: false,
    auto_process_suggestion_engine_ratings: true
  };

  let qualityProfiles = [];
  let duplicates = [];
  let pendingActions = [];
  let managedAccounts = [];
  let activeServer = 'plex';

  // UI state
  let accountsSidebarOpen = true;
  let fusionBuilderOpen = false;
  let settingsCollapsed = false;
  let collapsedByHover = false;
  let manuallyOpenedAccountsSidebar = false;

  // Queue filters
  let activeTab = 'suggestions';
  let queueFilterType = 'All';
  let queueFilterOriginator = 'All';
  let searchQuery = '';

  let pollingHandle = null;

  function decodeLabel(item) {
    return item?.title || decodeSyncId(item?.sync_id) || item?.sync_id || 'Unknown';
  }

  async function loadManagerSettings() {
    try {
      const r = await fetch('/api/manager/settings');
      if (r.ok) {
        const data = await r.json();
        settings = data.settings || settings;
      }
    } catch (e) { console.error(e); }
  }

  async function saveSettings() {
    try {
      await fetch('/api/manager/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) });
      alert('Settings saved');
    } catch (e) { console.error(e); alert('Save failed'); }
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

  // Persist small UI prefs in localStorage
// Persist small UI prefs in localStorage
  onMount(() => {
    // -> DELETED the try/catch block that was here <-
    
    loadManagerSettings();
    fetchDuplicates();
    fetchPendingActions();

    // Poll pending actions and duplicates every 8s
    pollingHandle = setInterval(() => {
      fetchPendingActions();
      fetchDuplicates();
    }, 8000);
  });

  onDestroy(() => {
    if (pollingHandle) clearInterval(pollingHandle);
  });

  function onMiniAccountsMouseEnter() {
    if (!manuallyOpenedAccountsSidebar) {
      collapsedByHover = true;
      accountsSidebarOpen = true;
    }
  }
  function onMiniAccountsMouseLeave() {
    if (collapsedByHover) {
      accountsSidebarOpen = false;
      collapsedByHover = false;
    }
  }

  function openAccountSidebarManually() {
    manuallyOpenedAccountsSidebar = true;
    accountsSidebarOpen = true;
  }

  // Actions
  async function runPruneJob() {
    if (!confirm('Run Prune Job?')) return;
    try {
      const r = await fetch('/api/manager/prune/run', { method: 'POST' });
      if (r.ok) { const j = await r.json(); alert(`Prune completed: ${j.result.deleted_count} deleted`); fetchDuplicates(); }
    } catch (e) { console.error(e); alert('Prune failed'); }
  }

  async function runManagerScan() {
    try {
      const r = await fetch('/api/manager/scan', { method: 'POST' });
      if (r.ok) { const j = await r.json(); alert('Scan complete'); fetchDuplicates(); fetchPendingActions(); }
    } catch (e) { console.error(e); alert('Scan failed'); }
  }

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

<section class="manager-page">
  <main class="main-column">
    <div class="card p-6">
        <div class="header-row">
          <div class="title-group">
            <h2>Manager Settings</h2>
            <div class="subtitle">Control automatic hygiene, upgrades, and staged actions</div>
          </div>
          <div class="actions">
            <button class="btn btn-ghost" on:click={() => settingsCollapsed = !settingsCollapsed} aria-pressed={settingsCollapsed}>
              {settingsCollapsed ? 'Expand' : 'Collapse'}
            </button>
            <button class="btn btn-primary" on:click={saveSettings}>Save</button>
            <button class="btn btn-ghost" on:click={runManagerScan}>Scan</button>
            <button class="btn btn-destructive" on:click={runPruneJob}>Prune</button>
          </div>
        </div>

      {#if !settingsCollapsed}
      <div class="settings-grid">
        <label class="row"><span>Enable Media Manager</span><input type="checkbox" bind:checked={settings.enabled} /></label>
        <label class="row"><span>Auto Delete Low Quality Duplicates</span><input type="checkbox" bind:checked={settings.auto_delete_low_quality_duplicates} /></label>
        <label class="row"><span>Auto Process Ratings</span><input type="checkbox" bind:checked={settings.auto_process_suggestion_engine_ratings} /></label>
      </div>
      {/if}

      <div class="queues-card mt-4">
        <div class="filter-bar">
            <input placeholder="Search by title, artist, or sync id" bind:value={searchQuery} class="input-search" />
            <div class="filter-group">
              <label class="filter-label">Type</label>
              <select bind:value={queueFilterType} class="filter-select"><option>All</option><option>Upgrade</option><option>Deletion</option><option>Duplicate Resolution</option></select>
            </div>
            <div class="filter-group">
              <label class="filter-label">Originator</label>
              <select bind:value={queueFilterOriginator} class="filter-select"><option>All</option><option>System</option><option>User</option></select>
            </div>
          </div>

          <div class="tabs-row" role="tablist" aria-label="Manager Tabs">
            <button role="tab" aria-selected={activeTab==='suggestions'} class="tab-btn" class:active={activeTab==='suggestions'} on:click={() => activeTab='suggestions'}>Suggestions & Requests</button>
            <button role="tab" aria-selected={activeTab==='pending'} class="tab-btn" class:active={activeTab==='pending'} on:click={() => activeTab='pending'}>Pending Actions</button>
          </div>

        <div class="mt-3">
          {#if activeTab === 'suggestions'}
            <div class="list-block">
              {#if filteredSuggestions.length === 0}
                <div class="empty">No suggestions.</div>
              {:else}
                {#each filteredSuggestions as item}
                  <div class="queue-item card-row">
                    <div class="queue-left">
                      <div class="title-row"><span class="badge muted">{item.type}</span><div class="title">{decodeLabel(item)}</div></div>
                      <div class="sub muted">{item.originator || 'System'}</div>
                    </div>
                    <div class="queue-actions">
                      <button class="btn btn-primary small" on:click={() => {/* approve */}}>Approve</button>
                      <button class="btn btn-ghost small" on:click={() => {/* reject */}}>Reject</button>
                    </div>
                  </div>
                {/each}
              {/if}
            </div>
          {:else}
            <div class="list-block">
              {#if filteredPendingActions.length === 0}
                <div class="empty">No pending actions.</div>
              {:else}
                {#each filteredPendingActions as item}
                  <div class="queue-item card-row">
                    <div class="queue-left">
                      <div class="title-row"><span class="badge muted">{item.action_needed}</span><div class="title">{decodeLabel(item)}</div></div>
                      <div class="sub muted">{item.artist || item.originator || 'Unknown'}</div>
                    </div>
                    <div class="queue-actions">
                      <button class="btn btn-ghost small" on:click={() => vetoPendingAction(item)}>Veto</button>
                      <button class="btn btn-primary small" on:click={() => executeNow(item)}>Execute</button>
                    </div>
                  </div>
                {/each}
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </main>

  <aside class="manager-sidebar">
    <div class="sidebar-panel card p-6">
      <div class="section-header-row">
        <h3>Managed Accounts</h3>
        <div class="actions"><button on:click={() => { accountsSidebarOpen = !accountsSidebarOpen; manuallyOpenedAccountsSidebar = accountsSidebarOpen; }} class="btn">{accountsSidebarOpen ? 'Hide' : 'Show'}</button></div>
      </div>

      {#if accountsSidebarOpen}
        <div class="sidebar-note">Active server: {activeServer}</div>
        <div class="accounts-grid">
          {#each managedAccounts as account}
            <div class="account-card">
              <div class="account-head"><div class="account-name">{account.display_name || account.account_name || `Account ${account.id}`}</div><div class="badge">{account.is_active ? 'Active' : 'Inactive'}</div></div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    {#if !accountsSidebarOpen}
      <div class="accounts-collapsed" on:mouseenter={onMiniAccountsMouseEnter} on:mouseleave={onMiniAccountsMouseLeave}>
        {#each managedAccounts as acc}
          <button class="mini-account" title={acc.display_name || acc.account_name} on:click={openAccountSidebarManually}>
            {#if acc.avatar_url}
              <img src={acc.avatar_url} alt={acc.display_name} />
            {:else}
              { (acc.display_name || acc.account_name || String(acc.id)).charAt(0).toUpperCase() }
            {/if}
          </button>
        {/each}
      </div>
    {/if}
  </aside>
</section>

<style>
.manager-page { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 20px; }
@media (max-width: 1100px) { .manager-page { grid-template-columns: 1fr; } }
.card { background: var(--glass); border: 1px solid var(--glass-border); border-radius: 12px; }
.p-6 { padding: 24px; }
.main-column { display: flex; flex-direction: column; gap: 16px; }
.settings-grid { display:flex; gap:12px; flex-wrap:wrap; }
.row { display:flex; align-items:center; gap:8px; }
.filter-bar { display:flex; gap:12px; align-items:center; margin-top:12px; }
.input-search { flex:1; padding:10px 12px; border-radius:10px; background: rgba(255,255,255,0.02); border:1px solid var(--glass-border); color:var(--text); }
.filter-group { display:flex; flex-direction:column; gap:6px; }
.filter-label { font-size:12px; color:var(--muted); }
.filter-select { padding:8px 10px; border-radius:8px; background: rgba(255,255,255,0.02); border:1px solid var(--glass-border); min-width:160px; }
.tabs-row { display:flex; gap:8px; margin-top:12px; }
.tab-btn { padding:10px 14px; border-radius:8px; background:transparent; border: none; cursor:pointer; color:var(--text); position:relative; }
.tab-btn.active::after { content: ''; position:absolute; left:8px; right:8px; bottom:-12px; height:3px; background:var(--color-primary); border-radius:3px; transform-origin:center; }
.list-block { margin-top:12px; border:1px solid var(--glass-border); border-radius:10px; padding:12px; min-height:160px; max-height:540px; overflow:auto; background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(0,0,0,0.02)); }
.queue-item { display:flex; justify-content:space-between; gap:12px; padding:12px; border-bottom:1px solid rgba(255,255,255,0.02); align-items:center; background:transparent; }
.queue-item:last-child { border-bottom:none; }
.card-row { display:flex; justify-content:space-between; align-items:center; gap:12px; }
.queue-left { display:flex; flex-direction:column; gap:6px; }
.title-row { display:flex; gap:8px; align-items:center; }
.badge { font-size:12px; padding:6px 8px; border-radius:999px; background:rgba(255,255,255,0.02); border:1px solid var(--glass-border); }
.badge.muted { opacity:0.8; }
.title { font-weight:600; font-size:14px; }
.sub { font-size:13px; color:var(--muted); }
.muted { color:var(--muted); }
.queue-actions { display:flex; gap:8px; }
.btn { padding:8px 10px; border-radius:8px; border:1px solid transparent; background:transparent; cursor:pointer; }
.btn.small { padding:6px 8px; font-size:13px; }
.btn-ghost { background:transparent; border:1px solid rgba(255,255,255,0.03); }
.btn-primary { background:var(--color-primary); color:white; }
.btn-destructive { background:#b04242; color:white; }
.btn-ghost.small { padding:6px 8px; }
.manager-sidebar { display:flex; flex-direction:column; gap:12px; }
.sidebar-panel { position: sticky; top: 20px; }
.accounts-collapsed { position: fixed; right: 12px; top: 140px; display:flex; flex-direction:column; gap:8px; z-index:60; }
.mini-account { width:44px; height:44px; border-radius:999px; background: rgba(255,255,255,0.03); border:1px solid var(--glass-border); display:flex; align-items:center; justify-content:center; }
.mini-account img { width:100%; height:100%; border-radius:999px; object-fit:cover; }

/* Responsive tweaks */
@media (max-width: 1100px) {
  .manager-page { grid-template-columns: 1fr; }
  .accounts-collapsed { right: 8px; top: 120px; }
}
</style>
