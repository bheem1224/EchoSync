<script>
    import { onMount } from 'svelte';
    import { decodeSyncId } from '../../../lib/utils';

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
    let managedAccounts = [];
    let activeServer = 'plex';
    let pendingActions = [];

    let loading = true;
    let pruneLoading = false;
    let scanLoading = false;
    let savingSettings = false;
    let actionLoadingSyncId = null;
    let syncingManagedUsers = false;

    onMount(async () => {
        await refreshAll();
    });

    async function refreshAll() {
        loading = true;
        try {
            await Promise.all([
                fetchSettings(),
                fetchQualityProfiles(),
                fetchDuplicates(),
                fetchManagedAccounts(),
                fetchPendingActions()
            ]);
        } finally {
            loading = false;
        }
    }

    async function fetchSettings() {
        try {
            const res = await fetch('/api/manager/settings');
            if (res.ok) {
                const data = await res.json();
                settings = {
                    ...settings,
                    ...(data.settings || {})
                };
            }
        } catch (e) { console.error(e); }
    }

    async function fetchQualityProfiles() {
        const profileEndpoints = ['/api/quality-profiles'];

        for (const url of profileEndpoints) {
            try {
                const res = await fetch(url);
                if (!res.ok) continue;
                const data = await res.json();
                const profiles = Array.isArray(data?.profiles) ? data.profiles : [];
                if (profiles.length > 0) {
                    qualityProfiles = profiles;
                    return;
                }
            } catch (e) {
                console.error(e);
            }
        }

        qualityProfiles = [];
    }

    async function saveSettings() {
        savingSettings = true;
        try {
            const res = await fetch('/api/manager/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            if (res.ok) {
                alert('Settings Saved');
                await fetchSettings();
            } else {
                alert('Failed to save settings');
            }
        } catch (e) { console.error(e); }
        finally { savingSettings = false; }
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

    async function fetchManagedAccounts() {
        try {
            const serverRes = await fetch('/api/media-server/active');
            if (!serverRes.ok) {
                managedAccounts = [];
                return;
            }

            const serverData = await serverRes.json();
            activeServer = serverData.active_server || 'plex';

            const accountRes = await fetch(`/api/accounts/${activeServer}`);
            if (!accountRes.ok) {
                managedAccounts = [];
                return;
            }

            const accountData = await accountRes.json();
            managedAccounts = accountData.accounts || [];
        } catch (e) { console.error(e); }
    }

    async function syncManagedUsers() {
        if (activeServer !== 'plex') return;

        syncingManagedUsers = true;
        try {
            const res = await fetch('/api/accounts/plex/sync_users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (res.ok) {
                const data = await res.json();
                managedAccounts = data.accounts || [];
            } else {
                const payload = await res.json().catch(() => ({}));
                alert(payload.error || 'Failed to sync managed users');
            }
        } catch (e) {
            console.error(e);
            alert('Failed to sync managed users');
        } finally {
            syncingManagedUsers = false;
        }
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

    async function runPruneJob() {
        if (!confirm('Run Prune Job? This will auto-delete low quality duplicates.')) return;
        pruneLoading = true;
        try {
            const res = await fetch('/api/manager/prune/run', { method: 'POST' });
            if (res.ok) {
                const result = await res.json();
                alert(`Prune Complete. Deleted ${result.result.deleted_count} tracks.`);
                await refreshAll();
            } else { alert('Prune Job Failed'); }
        } catch (e) { console.error(e); alert('Prune Job Error'); }
        finally { pruneLoading = false; }
    }

    async function runManagerScan() {
        scanLoading = true;
        try {
            const res = await fetch('/api/manager/scan', { method: 'POST' });
            if (res.ok) {
                const result = await res.json();
                const s = result.summary;
                alert(
                    `Scan Complete.\n` +
                    `Duplicates (auto-resolve): ${s.duplicates_auto_resolve}\n` +
                    `Duplicates (manual review): ${s.duplicates_manual_review}\n` +
                    `Staged for deletion: ${s.staged_deletes}\n` +
                    `Staged for upgrade: ${s.staged_upgrades}`
                );
                await refreshAll();
            } else {
                const payload = await res.json().catch(() => ({}));
                alert(payload.error || 'Scan failed');
            }
        } catch (e) { console.error(e); alert('Scan Error'); }
        finally { scanLoading = false; }
    }

    async function resolveConflict(keepId, tracks) {
        if (!confirm('Keep selected track and DELETE others?')) return;
        const deleteIds = tracks.filter(t => t.id !== keepId).map(t => t.id);
        try {
            const res = await fetch('/api/manager/conflicts/resolve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keep_id: keepId, delete_ids: deleteIds })
            });
            if (res.ok) {
                duplicates = duplicates.filter(group => !group.tracks.some(t => t.id === keepId));
            } else { alert('Failed to resolve conflict'); }
        } catch (e) { console.error(e); }
    }

    async function vetoPendingAction(item) {
        const isDelete = item.action_needed === 'DELETE_MONTH_END';
        const field = isDelete ? 'admin_exempt_deletion' : 'admin_force_upgrade';
        const value = isDelete ? true : false;

        actionLoadingSyncId = item.sync_id;
        try {
            const res = await fetch('/api/manager/suggestion-candidates/override', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sync_id: item.sync_id,
                    field,
                    value
                })
            });

            if (res.ok) {
                pendingActions = pendingActions.filter((entry) => entry.sync_id !== item.sync_id);
            } else { alert('Failed to process action'); }
        } catch (e) { console.error(e); }
        finally { actionLoadingSyncId = null; }
    }

    async function executeNow(item) {
        if (!item.track_id) {
            alert('Cannot execute action because this queued item is not linked to a track ID.');
            return;
        }

        const isDelete = item.action_needed === 'DELETE_MONTH_END';
        if (isDelete && !confirm('Are you sure? This action is irreversible.')) {
            return;
        }

        actionLoadingSyncId = item.sync_id;
        try {
            const endpoint = isDelete
                ? `/api/manager/track/${item.track_id}/force_delete`
                : `/api/manager/track/${item.track_id}/force_upgrade`;

            const reqInit = {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            };

            if (!isDelete) {
                reqInit.body = JSON.stringify({
                    quality_profile_id: settings.upgrade_quality_profile_id || null
                });
            }

            const res = await fetch(endpoint, reqInit);
            if (res.ok) {
                pendingActions = pendingActions.filter((entry) => entry.sync_id !== item.sync_id);
            } else {
                const payload = await res.json().catch(() => ({}));
                alert(payload.error || 'Action failed');
            }
        } catch (e) {
            console.error(e);
            alert('Action failed');
        } finally {
            actionLoadingSyncId = null;
        }
    }

    function getReadableTrackLabel(item) {
        return item?.title || decodeSyncId(item?.sync_id) || item?.sync_id || 'Unknown Track';
    }
</script>

<div class="animate-fade-in grid-layout h-full min-h-0 overflow-y-auto">

    <!-- Settings Panel -->
    <div class="card p-6">
        <div class="flex flex-col md:flex-row justify-between items-end gap-4">
            <div class="space-y-4 flex-1">
                <h2 class="flex items-center gap-2">
                    <span class="icon">⚙️</span>
                    Manager Settings
                </h2>

                <div class="settings-grid">
                    <div class="flex items-center gap-3">
                        <span class="text-sm font-medium">Enable Media Manager</span>
                        <label class="switch">
                            <input type="checkbox" bind:checked={settings.enabled}>
                            <span class="slider round"></span>
                        </label>
                    </div>

                    <div class="flex items-center gap-3">
                        <span class="text-sm font-medium">Auto-Delete Low Quality Duplicates</span>
                        <span class="info-icon" title="When enabled, duplicate clusters are automatically pruned by keeping the highest quality file and deleting lower quality copies.">i</span>
                        <label class="switch">
                            <input type="checkbox" bind:checked={settings.auto_delete_low_quality_duplicates}>
                            <span class="slider round"></span>
                        </label>
                    </div>

                    <div class="flex items-center gap-3">
                        <span class="text-sm font-medium">Auto-Process Suggestion Engine Ratings</span>
                        <span class="info-icon" title="When enabled, consensus scores are processed into weekly upgrade intents and month-end delete intents using the 10-point lifecycle model.">i</span>
                        <label class="switch">
                            <input type="checkbox" bind:checked={settings.auto_process_suggestion_engine_ratings}>
                            <span class="slider round"></span>
                        </label>
                    </div>

                    <div class="flex items-center gap-3">
                        <span class="text-sm font-medium">Auto Delete Staged Queue</span>
                        <span class="info-icon" title="When enabled, staged DELETE_MONTH_END actions older than 30 days are executed by the lifecycle processor.">i</span>
                        <label class="switch">
                            <input type="checkbox" bind:checked={settings.auto_delete}>
                            <span class="slider round"></span>
                        </label>
                    </div>

                    <div class="flex items-center gap-3">
                        <span class="text-sm font-medium">Auto Upgrade Staged Queue</span>
                        <span class="info-icon" title="When enabled, staged UPGRADE_WEEK_END actions older than 7 days are executed by the lifecycle processor.">i</span>
                        <label class="switch">
                            <input type="checkbox" bind:checked={settings.auto_upgrade}>
                            <span class="slider round"></span>
                        </label>
                    </div>

                    <div class="flex items-center gap-2">
                        <span class="text-sm muted">Upgrade Quality Profile:</span>
                        <select bind:value={settings.upgrade_quality_profile_id} class="input-select">
                            <option value="">Default</option>
                            {#each qualityProfiles as profile}
                                <option value={String(profile.id)}>{profile.name || profile.id}</option>
                            {/each}
                        </select>
                    </div>

                    <div class="flex items-center gap-2">
                        <span class="text-sm muted">Delete Threshold:</span>
                        <input type="number" bind:value={settings.delete_threshold} min="1" max="5" class="input-num">
                    </div>

                    <div class="flex items-center gap-2">
                        <span class="text-sm muted">Upgrade Threshold:</span>
                        <input type="number" bind:value={settings.upgrade_threshold} min="1" max="5" class="input-num">
                    </div>
                </div>

                <div class="info-block mt-3">
                    <p>
                        <strong>Duplicate Resolution:</strong> Detects duplicate tracks, keeps the highest quality copy
                        (bitrate and file size), and deletes inferior versions when auto-delete is enabled.
                    </p>
                    <p>
                        <strong>Suggestion Engine Thresholds:</strong> Scores 1-2 (0.5 to 1 star equivalent)
                        are scheduled for end-of-month deletion. Scores 3-4 are scheduled for weekly upgrades,
                        unless vetoed by an administrator.
                    </p>
                </div>
            </div>

            <div class="flex gap-4">
                <button on:click={saveSettings} disabled={savingSettings} class="btn btn--primary">
                    {#if savingSettings}Saving...{:else}Save Settings{/if}
                </button>
                <button on:click={runManagerScan} disabled={scanLoading} class="btn btn--secondary">
                    {#if scanLoading}Scanning...{:else}Run Manager Scan{/if}
                </button>
                <button on:click={runPruneJob} disabled={pruneLoading} class="btn btn--danger">
                    {#if pruneLoading}Running...{:else}Run Prune Job{/if}
                </button>
            </div>
        </div>
    </div>

    <div class="card p-6">
        <div class="section-header-row">
            <h2 class="mb-0">Managed Accounts ({activeServer})</h2>
            <div class="actions">
                {#if activeServer === 'plex'}
                    <button on:click={syncManagedUsers} disabled={syncingManagedUsers} class="btn btn--primary btn--small">
                        {#if syncingManagedUsers}
                            <span class="spinner" aria-hidden="true"></span>
                            Syncing...
                        {:else}
                            Sync Managed Users
                        {/if}
                    </button>
                {/if}
                <button on:click={fetchManagedAccounts} disabled={syncingManagedUsers} class="btn btn--ghost btn--small">Refresh Accounts</button>
            </div>
        </div>

        {#if managedAccounts.length === 0}
            <div class="empty compact">No managed accounts found for {activeServer}.</div>
        {:else}
            <div class="accounts-grid">
                {#each managedAccounts as account}
                    <div class="account-card">
                        <div class="account-head">
                            <div class="account-name">{account.display_name || account.account_name || `Account ${account.id}`}</div>
                            <span class="badge {account.is_active ? 'active' : 'inactive'}">{account.is_active ? 'Active' : 'Inactive'}</span>
                        </div>
                        <div class="account-meta">Account ID: {account.id}</div>
                    </div>
                {/each}
            </div>
        {/if}
    </div>

    <div class="queues-grid">

        <!-- Duplicate Resolution -->
        <div class="queue-col">
            <h2 class="queue-header">
                <span class="dot orange"></span>
                Duplicate Resolution
                <span class="count">({duplicates.length})</span>
            </h2>

            <div class="card queue-list">
                {#if duplicates.length === 0}
                    <div class="empty">No conflicts found.</div>
                {:else}
                    <div class="list-content">
                        {#each duplicates as group}
                            <div class="group-item">
                                <div class="group-meta">
                                    <span class="fp">FP: {group.chromaprint.substring(0, 8)}...</span>
                                    {#if group.type === 'auto_resolve'}
                                        <span class="badge-type quality">Quality Ranked</span>
                                    {:else}
                                        <span class="badge-type conflict">Metadata Conflict</span>
                                    {/if}
                                </div>
                                <div class="tracks-stack">
                                    {#each group.tracks as track}
                                        {@const isRecommended = group.recommended_keep_id === track.id}
                                        <div class="track-option" class:recommended={isRecommended}>
                                            <div class="info">
                                                <div class="header-row">
                                                    <div class="title">{track.title}</div>
                                                    {#if isRecommended}
                                                        <span class="badge-type keep-rec">Keep</span>
                                                    {:else if group.recommended_keep_id}
                                                        <span class="badge-type del-rec">Lower Quality</span>
                                                    {/if}
                                                </div>
                                                <div class="artist">{track.artist}</div>
                                                <div class="meta">
                                                    {track.bitrate ? Math.round(track.bitrate/1000) + 'k' : '?'} •
                                                    {track.sample_rate ? track.sample_rate + 'Hz' : '?'} •
                                                    {track.file_size ? (track.file_size/1024/1024).toFixed(1) + 'MB' : '?'} •
                                                    {track.format || '?'}
                                                </div>
                                            </div>
                                            <button
                                                on:click={() => resolveConflict(track.id, group.tracks)}
                                                class="btn btn--small {isRecommended ? 'btn--success' : 'btn--ghost'}"
                                            >
                                                {isRecommended ? 'Keep (Recommended)' : 'Keep This'}
                                            </button>
                                        </div>
                                    {/each}
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>

        <!-- Pending Actions (staged queue) -->
        <div class="queue-col">
            <h2 class="queue-header">
                <span class="dot blue"></span>
                Pending Actions
                <span class="count">({pendingActions.length})</span>
            </h2>

            <div class="card queue-list">
                {#if pendingActions.length === 0}
                    <div class="empty">No staged lifecycle actions.</div>
                {:else}
                    <div class="list-content suggestion-list">
                        {#each pendingActions as item}
                            <div class="action-item">
                                <div class="info">
                                    <div class="header-row">
                                        <span class="badge {item.action_needed === 'DELETE_MONTH_END' ? 'delete' : 'upgrade'}">
                                            {item.action_needed === 'DELETE_MONTH_END' ? 'Pending Delete' : 'Pending Upgrade'}
                                        </span>
                                        <span class="title" title={item.sync_id}>{getReadableTrackLabel(item)}</span>
                                    </div>
                                    <div class="artist">{item.artist || 'Unknown Artist'}</div>
                                    <div class="meta">In queue: {item.days_in_queue ?? 0} day(s)</div>
                                </div>

                                <div class="actions">
                                    <button
                                        on:click={() => vetoPendingAction(item)}
                                        class="btn btn--small btn--success"
                                        disabled={actionLoadingSyncId === item.sync_id}
                                        title="Veto this queued action"
                                    >
                                        Veto
                                    </button>

                                    <button
                                        on:click={() => executeNow(item)}
                                        class={`btn btn--small ${item.action_needed === 'DELETE_MONTH_END' ? 'btn--danger' : 'btn--primary'}`}
                                        disabled={actionLoadingSyncId === item.sync_id || !item.track_id}
                                        title={!item.track_id ? 'Track ID unavailable for this sync item' : 'Execute action immediately'}
                                    >
                                        {item.action_needed === 'DELETE_MONTH_END' ? 'Delete Now' : 'Upgrade Now'}
                                    </button>
                                </div>
                            </div>
                        {/each}

                        <div class="info-block compact">
                            <p>
                                Veto marks delete actions as exempt and removes queued items from this staging view.
                            </p>
                            <p>
                                Execute Now bypasses queue timers. Delete actions require explicit confirmation.
                            </p>
                        </div>
                    </div>
                {/if}
            </div>
        </div>

    </div>

    {#if loading}
        <div class="loading-note">Loading manager data...</div>
    {/if}
</div>

<style>
    .grid-layout { display: flex; flex-direction: column; gap: 24px; }
    .card { background: var(--glass); border: 1px solid var(--glass-border); border-radius: 12px; overflow: hidden; }
    .p-6 { padding: 24px; }

    h2 { font-size: 18px; font-weight: 600; color: var(--text); margin: 0 0 12px 0; }
    .mb-0 { margin-bottom: 0; }
    .mt-3 { margin-top: 12px; }
    .muted { color: var(--muted); }
    .icon { font-size: 18px; }

    .settings-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; align-items: center; }

    .input-num {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 4px; color: var(--text); width: 60px; padding: 4px 8px; text-align: center;
    }

    .input-select {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 6px;
        color: var(--text);
        min-width: 180px;
        padding: 6px 8px;
    }

    .info-icon {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: 700;
        color: var(--muted);
        border: 1px solid var(--glass-border);
        cursor: help;
    }

    .info-block {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--glass-border);
        border-radius: 10px;
        padding: 10px 12px;
        color: var(--muted);
        font-size: 12px;
        line-height: 1.45;
        display: grid;
        gap: 6px;
    }

    .info-block.compact { margin: 12px; }

    .section-header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
    }

    .accounts-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
    }

    .account-card {
        border: 1px solid var(--glass-border);
        background: rgba(255,255,255,0.02);
        border-radius: 10px;
        padding: 12px;
    }

    .account-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .account-name { font-size: 14px; font-weight: 700; color: var(--text); }
    .account-meta { font-size: 12px; color: var(--muted); margin-top: 4px; }

    /* Toggle Switch */
    .switch { position: relative; display: inline-block; width: 40px; height: 24px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: rgba(255,255,255,0.1); transition: .4s; border-radius: 24px; border: 1px solid rgba(255,255,255,0.1); }
    .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px; background-color: #94a3b8; transition: .4s; border-radius: 50%; }
    input:checked + .slider { background-color: rgba(15, 239, 136, 0.2); border-color: var(--accent); }
    input:checked + .slider:before { transform: translateX(16px); background-color: var(--accent); }

    .btn { padding: 8px 16px; border-radius: 8px; font-weight: 600; font-size: 13px; border: none; cursor: pointer; transition: all 0.2s; }
    .btn--primary { background: var(--accent); color: #000; }
    .btn--primary:hover { opacity: 0.9; transform: translateY(-1px); }
    .btn--danger { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .btn--danger:hover { background: rgba(239, 68, 68, 0.3); }
    .btn--success { background: rgba(34, 197, 94, 0.1); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.2); }
    .btn--success:hover { background: rgba(34, 197, 94, 0.2); }
    .btn--small { padding: 6px 10px; font-size: 11px; }
    .btn--ghost { background: rgba(255,255,255,0.05); color: var(--text); border: 1px solid var(--glass-border); }
    .btn--ghost:hover { background: rgba(255,255,255,0.08); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .spinner {
        width: 12px;
        height: 12px;
        border: 2px solid rgba(0, 0, 0, 0.2);
        border-top-color: currentColor;
        border-radius: 50%;
        display: inline-block;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }

    .queues-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media (max-width: 980px) { .queues-grid { grid-template-columns: 1fr; } }

    .queue-col { display: flex; flex-direction: column; gap: 12px; }
    .queue-header { display: flex; align-items: center; font-size: 16px; margin: 0; }
    .dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
    .dot.orange { background: #f97316; }
    .dot.blue { background: #3b82f6; }
    .count { font-weight: 400; color: var(--muted); margin-left: 8px; font-size: 14px; }

    .queue-list { min-height: 400px; max-height: 650px; display: flex; flex-direction: column; }
    .list-content { overflow-y: auto; flex: 1; }
    .suggestion-list { display: flex; flex-direction: column; gap: 12px; }
    .empty { padding: 40px; text-align: center; color: var(--muted); }
    .empty.compact { padding: 10px; }

    /* Hygiene Items */
    .group-item { padding: 16px; border-bottom: 1px solid var(--glass-border); }
    .group-item:last-child { border-bottom: none; }
    .group-item:hover { background: rgba(255,255,255,0.02); }
    .group-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .fp { font-family: monospace; font-size: 11px; color: var(--muted); }

    .badge-type { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; white-space: nowrap; }
    .badge-type.quality { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge-type.conflict { background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }
    .badge-type.keep-rec { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
    .badge-type.del-rec { background: rgba(239, 68, 68, 0.1); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.25); }

    .tracks-stack { display: flex; flex-direction: column; gap: 8px; }
    .track-option { background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px; display: flex; justify-content: space-between; align-items: center; gap: 12px; border: 1px solid transparent; }
    .track-option.recommended { border-color: rgba(34, 197, 94, 0.25); background: rgba(34, 197, 94, 0.04); }
    .info { overflow: hidden; flex: 1; min-width: 0; }
    .title { font-weight: 600; font-size: 13px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .artist { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .meta { font-size: 11px; color: var(--muted); opacity: 0.8; margin-top: 2px; }

    /* Candidate / action items */
    .candidate-block { border-top: 1px solid var(--glass-border); }
    .candidate-block:first-child { border-top: none; }
    .candidate-title { font-size: 13px; color: var(--muted); padding: 12px 16px 0; text-transform: uppercase; letter-spacing: 0.04em; }
    .action-item { padding: 16px; border-bottom: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .action-item:hover { background: rgba(255,255,255,0.02); }
    .header-row { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
    .badge { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
    .badge.delete { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge.upgrade { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .badge.active { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
    .badge.inactive { background: rgba(148, 163, 184, 0.15); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.3); }
    .actions { display: flex; gap: 8px; }

    .loading-note {
        color: var(--muted);
        font-size: 12px;
        text-align: right;
    }
</style>
