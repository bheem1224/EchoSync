<script>
    import { onMount } from 'svelte';

    let settings = {
        enabled: true,
        delete_threshold: 1,
        upgrade_threshold: 2,
        auto_delete_low_quality_duplicates: false,
        auto_process_suggestion_engine_ratings: true
    };
    let duplicates = [];
    let managedAccounts = [];
    let activeServer = 'plex';
    let deleteCandidates = [];
    let upgradeCandidates = [];

    let loading = true;
    let pruneLoading = false;
    let savingSettings = false;
    let vetoLoadingSyncId = null;

    onMount(async () => {
        await refreshAll();
    });

    async function refreshAll() {
        loading = true;
        try {
            await Promise.all([
                fetchSettings(),
                fetchDuplicates(),
                fetchManagedAccounts(),
                fetchSuggestionCandidates()
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
                settings = data.settings;
            }
        } catch (e) { console.error(e); }
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

    async function fetchSuggestionCandidates() {
        try {
            const res = await fetch('/api/manager/suggestion-candidates?limit=100');
            if (res.ok) {
                const data = await res.json();
                deleteCandidates = data.delete_candidates || [];
                upgradeCandidates = data.upgrade_candidates || [];
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

    async function toggleOverride(syncId, field, currentValue) {
        vetoLoadingSyncId = syncId;
        try {
            const res = await fetch('/api/manager/suggestion-candidates/override', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sync_id: syncId,
                    field,
                    value: !currentValue
                })
            });

            if (res.ok) {
                const payload = await res.json();
                const state = payload.state || {};

                deleteCandidates = deleteCandidates.map((candidate) =>
                    candidate.sync_id === syncId
                        ? {
                            ...candidate,
                            admin_exempt_deletion: !!state.admin_exempt_deletion,
                            admin_force_upgrade: !!state.admin_force_upgrade
                        }
                        : candidate
                );

                upgradeCandidates = upgradeCandidates.map((candidate) =>
                    candidate.sync_id === syncId
                        ? {
                            ...candidate,
                            admin_exempt_deletion: !!state.admin_exempt_deletion,
                            admin_force_upgrade: !!state.admin_force_upgrade
                        }
                        : candidate
                );
            } else { alert('Failed to process action'); }
        } catch (e) { console.error(e); }
        finally { vetoLoadingSyncId = null; }
    }
</script>

<div class="animate-fade-in grid-layout">

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
                <button on:click={runPruneJob} disabled={pruneLoading} class="btn btn--danger">
                    {#if pruneLoading}Running...{:else}Run Prune Job{/if}
                </button>
            </div>
        </div>
    </div>

    <div class="card p-6">
        <div class="section-header-row">
            <h2 class="mb-0">Managed Accounts ({activeServer})</h2>
            <button on:click={fetchManagedAccounts} class="btn btn--ghost btn--small">Refresh Accounts</button>
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
                                    <span class="fp">FP: {group.fingerprint_hash.substring(0, 8)}...</span>
                                </div>
                                <div class="tracks-stack">
                                    {#each group.tracks as track}
                                        <div class="track-option">
                                            <div class="info">
                                                <div class="title">{track.title}</div>
                                                <div class="artist">{track.artist}</div>
                                                <div class="meta">{track.bitrate ? Math.round(track.bitrate/1000) + 'k' : '?'} • {track.sample_rate}Hz • {(track.file_size/1024/1024).toFixed(1)}MB</div>
                                            </div>
                                            <button
                                                on:click={() => resolveConflict(track.id, group.tracks)}
                                                class="btn btn--small btn--success"
                                            >
                                                Keep This
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

        <!-- Suggestion Engine Veto / Exemption Controls -->
        <div class="queue-col">
            <h2 class="queue-header">
                <span class="dot blue"></span>
                Suggestion Engine Controls
                <span class="count">({deleteCandidates.length + upgradeCandidates.length})</span>
            </h2>

            <div class="card queue-list">
                {#if deleteCandidates.length === 0 && upgradeCandidates.length === 0}
                    <div class="empty">No threshold candidates found.</div>
                {:else}
                    <div class="list-content suggestion-list">
                        <div class="candidate-block">
                            <h3 class="candidate-title">Delete Candidates (Score 1-2)</h3>
                            {#if deleteCandidates.length === 0}
                                <div class="empty compact">No delete candidates.</div>
                            {:else}
                                {#each deleteCandidates as candidate}
                                    <div class="action-item">
                                        <div class="info">
                                            <div class="header-row">
                                                <span class="badge delete">delete_month_end</span>
                                                <span class="title" title={candidate.sync_id}>{candidate.sync_id}</span>
                                            </div>
                                            <div class="meta">Score: {candidate.score_10} • Ratings: {candidate.ratings_count}</div>
                                        </div>

                                        <div class="actions">
                                            <button
                                                on:click={() => toggleOverride(candidate.sync_id, 'admin_exempt_deletion', candidate.admin_exempt_deletion)}
                                                class="btn btn--small {candidate.admin_exempt_deletion ? 'btn--danger' : 'btn--success'}"
                                                disabled={vetoLoadingSyncId === candidate.sync_id}
                                                title="Toggle admin_exempt_deletion"
                                            >
                                                {candidate.admin_exempt_deletion ? 'Remove Veto' : 'Veto Deletion'}
                                            </button>
                                        </div>
                                    </div>
                                {/each}
                            {/if}
                        </div>

                        <div class="candidate-block">
                            <h3 class="candidate-title">Upgrade Candidates (Score 3-4)</h3>
                            {#if upgradeCandidates.length === 0}
                                <div class="empty compact">No upgrade candidates.</div>
                            {:else}
                                {#each upgradeCandidates as candidate}
                                    <div class="action-item">
                                        <div class="info">
                                            <div class="header-row">
                                                <span class="badge upgrade">upgrade_week_end</span>
                                                <span class="title" title={candidate.sync_id}>{candidate.sync_id}</span>
                                            </div>
                                            <div class="meta">Score: {candidate.score_10} • Ratings: {candidate.ratings_count}</div>
                                        </div>

                                        <div class="actions">
                                            <button
                                                on:click={() => toggleOverride(candidate.sync_id, 'admin_force_upgrade', candidate.admin_force_upgrade)}
                                                class="btn btn--small {candidate.admin_force_upgrade ? 'btn--primary' : 'btn--ghost'}"
                                                disabled={vetoLoadingSyncId === candidate.sync_id}
                                                title="Toggle admin_force_upgrade"
                                            >
                                                {candidate.admin_force_upgrade ? 'Force Upgrade On' : 'Force Upgrade Off'}
                                            </button>
                                        </div>
                                    </div>
                                {/each}
                            {/if}
                        </div>

                        <div class="info-block compact">
                            <p>
                                Use the controls above to toggle <strong>admin_exempt_deletion</strong> and
                                <strong>admin_force_upgrade</strong> flags in working.db for each sync_id.
                            </p>
                            <p>
                                These flags are consumed by the lifecycle gate and can veto deletion or force upgrade intents.
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
    h3 { margin: 0; color: var(--text); }
    .mb-0 { margin-bottom: 0; }
    .mt-3 { margin-top: 12px; }
    .muted { color: var(--muted); }
    .icon { font-size: 18px; }

    .settings-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; align-items: center; }

    .input-num {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 4px; color: var(--text); width: 60px; padding: 4px 8px; text-align: center;
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
    .group-meta { display: flex; justify-content: space-between; margin-bottom: 8px; }
    .fp { font-family: monospace; font-size: 11px; color: var(--muted); }

    .tracks-stack { display: flex; flex-direction: column; gap: 8px; }
    .track-option { background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px; display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .info { overflow: hidden; }
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
