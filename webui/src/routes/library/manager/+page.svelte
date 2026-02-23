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
                await fetchActionQueue(); // Refresh queue as thresholds changed
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
        // type: 'lock' (Pardon), 'delete' (Approve Delete), 'upgrade' (Approve Upgrade)
        // Map to backend override action
        let action = type;
        if (type === 'lock') action = 'lock';
        // If type is 'delete' or 'upgrade' passed from UI, it matches backend.

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

<div class="space-y-8 animate-fade-in">

    <!-- Settings Panel -->
    <div class="bg-gray-800 p-6 rounded-xl border border-gray-700">
        <div class="flex flex-col md:flex-row justify-between items-end gap-4">
            <div class="space-y-4 flex-1">
                <h2 class="text-lg font-bold text-white flex items-center gap-2">
                    <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                    Manager Settings
                </h2>

                <div class="flex items-center gap-6">
                    <label class="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" bind:checked={settings.enabled} class="form-checkbox h-5 w-5 text-blue-600 rounded bg-gray-700 border-gray-600">
                        <span class="text-gray-300">Enable Media Manager</span>
                    </label>

                    <div class="flex items-center gap-2">
                        <span class="text-sm text-gray-400">Delete Threshold:</span>
                        <input type="number" bind:value={settings.delete_threshold} min="1" max="5" class="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-center">
                    </div>

                    <div class="flex items-center gap-2">
                        <span class="text-sm text-gray-400">Upgrade Threshold:</span>
                        <input type="number" bind:value={settings.upgrade_threshold} min="1" max="5" class="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-center">
                    </div>
                </div>
            </div>

            <div class="flex gap-4">
                <button
                    on:click={saveSettings}
                    class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                >
                    Save Settings
                </button>
                <button
                    on:click={runPruneJob}
                    disabled={pruneLoading}
                    class="bg-red-900/50 border border-red-700 hover:bg-red-800 text-red-200 px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
                >
                    {#if pruneLoading}Loading...{:else}Run Prune Job{/if}
                </button>
            </div>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">

        <!-- Duplicate Resolution -->
        <div class="space-y-4">
            <h2 class="text-xl font-semibold flex items-center gap-2 text-orange-400">
                <span class="w-2 h-2 rounded-full bg-orange-500"></span>
                Duplicate Resolution
                <span class="text-sm font-normal text-gray-500 ml-2">({duplicates.length})</span>
            </h2>

            <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden min-h-[400px]">
                {#if duplicates.length === 0}
                    <div class="p-8 text-center text-gray-500">No conflicts found.</div>
                {:else}
                    <div class="divide-y divide-gray-700">
                        {#each duplicates as group}
                            <div class="p-4 hover:bg-white/5">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-xs font-mono text-gray-500">FP: {group.fingerprint_hash.substring(0, 8)}...</span>
                                </div>
                                <div class="space-y-2">
                                    {#each group.tracks as track}
                                        <div class="flex items-center justify-between bg-black/20 p-2 rounded border border-white/5">
                                            <div class="flex-1 min-w-0 mr-2">
                                                <div class="font-bold text-sm text-white truncate">{track.title}</div>
                                                <div class="text-xs text-gray-400 truncate">{track.artist}</div>
                                                <div class="text-[10px] text-gray-500">{track.bitrate ? Math.round(track.bitrate/1000) + 'k' : '?'} • {track.sample_rate}Hz • {(track.file_size/1024/1024).toFixed(1)}MB</div>
                                            </div>
                                            <button
                                                on:click={() => resolveConflict(track.id, group.tracks)}
                                                class="bg-green-600/20 hover:bg-green-600/40 text-green-400 text-xs px-3 py-1 rounded border border-green-600/50"
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
        <div class="space-y-4">
            <h2 class="text-xl font-semibold flex items-center gap-2 text-blue-400">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                Pending Actions
                <span class="text-sm font-normal text-gray-500 ml-2">({actionQueue.length})</span>
            </h2>

            <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden min-h-[400px]">
                {#if actionQueue.length === 0}
                    <div class="p-8 text-center text-gray-500">No pending actions.</div>
                {:else}
                    <div class="divide-y divide-gray-700">
                        {#each actionQueue as track}
                            <div class="p-4 hover:bg-white/5 flex items-center justify-between gap-4">
                                <div class="min-w-0 flex-1">
                                    <div class="flex items-center gap-2 mb-1">
                                        <span class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border {track.action_needed === 'delete' ? 'bg-red-900/50 text-red-200 border-red-800' : 'bg-blue-900/50 text-blue-200 border-blue-800'}">
                                            {track.action_needed}
                                        </span>
                                        <span class="text-sm font-medium text-white truncate">{track.title}</span>
                                    </div>
                                    <div class="text-xs text-gray-400 truncate">{track.artist}</div>
                                    <div class="text-xs text-gray-500 mt-1">Consensus Rating: {track.current_rating}</div>
                                </div>

                                <div class="flex items-center gap-2 shrink-0">
                                    <button
                                        on:click={() => handleAction(track.id, 'lock')}
                                        class="p-2 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
                                        title="Pardon (Lock)"
                                    >
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
                                    </button>

                                    <button
                                        on:click={() => handleAction(track.id, track.action_needed)}
                                        class="p-2 hover:bg-gray-700 rounded text-green-400 hover:text-green-300 transition-colors"
                                        title="Approve Action"
                                    >
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                                    </button>
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>

    </div>
</div>
