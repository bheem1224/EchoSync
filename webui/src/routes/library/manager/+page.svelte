<script>
    import { onMount } from 'svelte';

    let settings = { enabled: true, delete_threshold: 1, upgrade_threshold: 2 };
    let duplicates = [];
    let actionQueue = [];
    let loading = true;
    let pruneLoading = false;

    onMount(async () => {
        await refreshAll();
    });

    async function refreshAll() {
        loading = true;
        try {
            await Promise.all([
                fetchSettings(),
                fetchDuplicates(),
                fetchActionQueue()
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
        try {
            const res = await fetch('/api/manager/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            if (res.ok) {
                alert('Settings Saved');
                await fetchActionQueue();
            }
        } catch (e) { console.error(e); }
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

    async function fetchActionQueue() {
        try {
            const res = await fetch('/api/manager/queue/actions');
            if (res.ok) {
                const data = await res.json();
                actionQueue = data.queue || [];
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

    async function handleAction(id, type) {
        let action = type;
        if (type === 'lock') action = 'lock';
        try {
            const res = await fetch(`/api/manager/track/${id}/override`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action })
            });
            if (res.ok) {
                actionQueue = actionQueue.filter(t => t.id !== id);
            } else { alert('Failed to process action'); }
        } catch (e) { console.error(e); }
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

                <div class="flex items-center gap-6 flex-wrap">
                    <div class="flex items-center gap-3">
                        <span class="text-sm font-medium">Enable Media Manager</span>
                        <label class="switch">
                            <input type="checkbox" bind:checked={settings.enabled}>
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
            </div>

            <div class="flex gap-4">
                <button on:click={saveSettings} class="btn btn--primary">Save Settings</button>
                <button on:click={runPruneJob} disabled={pruneLoading} class="btn btn--danger">
                    {#if pruneLoading}Running...{:else}Run Prune Job{/if}
                </button>
            </div>
        </div>
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

        <!-- Pending Actions -->
        <div class="queue-col">
            <h2 class="queue-header">
                <span class="dot blue"></span>
                Pending Actions
                <span class="count">({actionQueue.length})</span>
            </h2>

            <div class="card queue-list">
                {#if actionQueue.length === 0}
                    <div class="empty">No pending actions.</div>
                {:else}
                    <div class="list-content">
                        {#each actionQueue as track}
                            <div class="action-item">
                                <div class="info">
                                    <div class="header-row">
                                        <span class="badge {track.action_needed}">{track.action_needed}</span>
                                        <span class="title" title={track.title}>{track.title}</span>
                                    </div>
                                    <div class="artist">{track.artist}</div>
                                    <div class="meta">Consensus Rating: {track.current_rating}</div>
                                </div>

                                <div class="actions">
                                    <button on:click={() => handleAction(track.id, 'lock')} class="btn btn--icon" title="Pardon (Lock)">🔒</button>
                                    <button on:click={() => handleAction(track.id, track.action_needed)} class="btn btn--icon success" title="Approve">✓</button>
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>

    </div>
</div>

<style>
    .grid-layout { display: flex; flex-direction: column; gap: 24px; }
    .card { background: var(--glass); border: 1px solid var(--glass-border); border-radius: 12px; overflow: hidden; }
    .p-6 { padding: 24px; }

    h2 { font-size: 18px; font-weight: 600; color: var(--text); margin: 0 0 12px 0; }
    .muted { color: var(--muted); }
    .icon { font-size: 18px; }

    .input-num {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
        border-radius: 4px; color: var(--text); width: 60px; padding: 4px 8px; text-align: center;
    }

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
    .btn--small { padding: 4px 10px; font-size: 11px; }
    .btn--icon { background: rgba(255,255,255,0.05); width: 32px; height: 32px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 50%; }
    .btn--icon:hover { background: rgba(255,255,255,0.1); }
    .btn--icon.success:hover { color: #4ade80; background: rgba(34, 197, 94, 0.1); }

    .queues-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media (max-width: 900px) { .queues-grid { grid-template-columns: 1fr; } }

    .queue-col { display: flex; flex-direction: column; gap: 12px; }
    .queue-header { display: flex; align-items: center; font-size: 16px; margin: 0; }
    .dot { width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
    .dot.orange { background: #f97316; }
    .dot.blue { background: #3b82f6; }
    .count { font-weight: 400; color: var(--muted); margin-left: 8px; font-size: 14px; }

    .queue-list { min-height: 400px; max-height: 600px; display: flex; flex-direction: column; }
    .list-content { overflow-y: auto; flex: 1; }
    .empty { padding: 40px; text-align: center; color: var(--muted); }

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
    .meta { font-size: 11px; color: var(--muted); opacity: 0.7; margin-top: 2px; }

    /* Action Items */
    .action-item { padding: 16px; border-bottom: 1px solid var(--glass-border); display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .action-item:hover { background: rgba(255,255,255,0.02); }
    .header-row { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
    .badge { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
    .badge.delete { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge.upgrade { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
    .actions { display: flex; gap: 8px; }
</style>
