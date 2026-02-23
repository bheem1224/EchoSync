<script>
    import { onMount } from 'svelte';
    import Omnibar from '$lib/components/Omnibar.svelte';

    // Remove Omnibar from here if it is going to be in the parent library page
    // Actually, the prompt says "change the search of library".
    // If we use Omnibar in the parent, we might not need it here, or we keep it for consistency.
    // But in a "Tab" layout, the Omnibar usually sits above the tabs or within the Library tab.
    // The prompt says "implement the frontend dashboard as a separate tab in the library page".
    // I will remove the Omnibar from this component since it will be lifted to the parent or Library tab.

    let trends = { total_ratings: 0, average_rating: 0, distribution: {} };
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
                fetchTrends(),
                fetchDuplicates(),
                fetchActionQueue()
            ]);
        } finally {
            loading = false;
        }
    }

    async function fetchTrends() {
        try {
            const res = await fetch('/api/manager/trends');
            if (res.ok) trends = await res.json();
        } catch (e) {
            console.error(e);
        }
    }

    async function fetchDuplicates() {
        try {
            const res = await fetch('/api/manager/duplicates');
            if (res.ok) {
                const data = await res.json();
                duplicates = data.duplicates || [];
            }
        } catch (e) {
            console.error(e);
        }
    }

    async function fetchActionQueue() {
        try {
            const res = await fetch('/api/manager/queue/actions');
            if (res.ok) {
                const data = await res.json();
                actionQueue = data.queue || [];
            }
        } catch (e) {
            console.error(e);
        }
    }

    async function runPruneJob() {
        if (!confirm('Are you sure you want to run the Prune Job? This will delete auto-resolved duplicates.')) return;

        pruneLoading = true;
        try {
            const res = await fetch('/api/manager/prune/run', { method: 'POST' });
            if (res.ok) {
                const result = await res.json();
                alert(`Prune Complete. Deleted ${result.result.deleted_count} tracks.`);
                await refreshAll();
            } else {
                alert('Prune Job Failed');
            }
        } catch (e) {
            console.error(e);
            alert('Prune Job Error');
        } finally {
            pruneLoading = false;
        }
    }

    async function resolveConflict(keepId, tracks) {
        if (!confirm('This will keep the selected track and DELETE all others in this group. Continue?')) return;

        const deleteIds = tracks.filter(t => t.id !== keepId).map(t => t.id);

        try {
            const res = await fetch('/api/manager/conflicts/resolve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keep_id: keepId, delete_ids: deleteIds })
            });

            if (res.ok) {
                duplicates = duplicates.filter(group => !group.tracks.some(t => t.id === keepId));
            } else {
                alert('Failed to resolve conflict');
            }
        } catch (e) {
            console.error(e);
            alert('Error resolving conflict');
        }
    }

    async function overrideTrack(id, action) {
        try {
            const res = await fetch(`/api/manager/track/${id}/override`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action })
            });

            if (res.ok) {
                actionQueue = actionQueue.filter(t => t.id !== id);
            } else {
                alert('Failed to override track');
            }
        } catch (e) {
            console.error(e);
            alert('Error overriding track');
        }
    }
</script>

<div class="space-y-8">

    <!-- Top Stats Section -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700">
            <h3 class="text-gray-400 text-xs uppercase tracking-wider mb-1">Total Ratings</h3>
            <span class="text-2xl font-bold">{trends.total_ratings}</span>
        </div>
        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700">
            <h3 class="text-gray-400 text-xs uppercase tracking-wider mb-1">Avg Rating</h3>
            <span class="text-2xl font-bold text-yellow-400">{trends.average_rating.toFixed(2)}</span>
        </div>
        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 md:col-span-2 flex items-center justify-between">
            <div>
                <h3 class="text-gray-400 text-xs uppercase tracking-wider mb-1">Prune Job</h3>
                <p class="text-xs text-gray-500">Auto-delete low quality duplicates</p>
            </div>
            <button
                on:click={runPruneJob}
                disabled={pruneLoading}
                class="bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
            >
                {#if pruneLoading}
                    <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    Running...
                {:else}
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    Run Prune Now
                {/if}
            </button>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">

        <!-- Hygiene Queue -->
        <div class="space-y-4">
            <div class="flex items-center justify-between">
                <h2 class="text-xl font-semibold flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-orange-500"></span>
                    Hygiene Queue
                    <span class="text-sm font-normal text-gray-500 ml-2">Manual Review ({duplicates.length})</span>
                </h2>
            </div>

            <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden min-h-[400px]">
                {#if duplicates.length === 0}
                    <div class="p-8 text-center text-gray-500">No manual review items found.</div>
                {:else}
                    <div class="divide-y divide-gray-700">
                        {#each duplicates as group}
                            <div class="p-4 hover:bg-gray-750 transition-colors">
                                <div class="flex items-center justify-between mb-3">
                                    <span class="text-xs font-mono text-gray-500 truncate" title={group.fingerprint_hash}>
                                        FP: {group.fingerprint_hash.substring(0, 8)}...
                                    </span>
                                    <span class="bg-orange-900/50 text-orange-200 text-xs px-2 py-0.5 rounded border border-orange-800">Conflict</span>
                                </div>

                                <div class="space-y-2 mb-4">
                                    {#each group.tracks as track}
                                        <div class="flex items-center justify-between bg-gray-900/50 p-2 rounded border border-gray-700">
                                            <div class="flex-1 min-w-0 mr-4">
                                                <div class="font-medium text-sm text-white truncate">{track.title}</div>
                                                <div class="text-xs text-gray-400 truncate">{track.artist} • {track.album}</div>
                                                <div class="text-[10px] text-gray-500 mt-1 flex gap-2">
                                                    <span>{track.bitrate ? Math.round(track.bitrate/1000) + 'kbps' : 'Unknown'}</span>
                                                    <span>{track.sample_rate}Hz</span>
                                                    <span>{(track.file_size / 1024 / 1024).toFixed(1)}MB</span>
                                                </div>
                                            </div>
                                            <button
                                                on:click={() => resolveConflict(track.id, group.tracks)}
                                                class="shrink-0 bg-green-600/20 hover:bg-green-600/40 text-green-400 text-xs px-3 py-1.5 rounded border border-green-600/50 transition-colors"
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

        <!-- Action Queue -->
        <div class="space-y-4">
            <div class="flex items-center justify-between">
                <h2 class="text-xl font-semibold flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                    Action Queue
                    <span class="text-sm font-normal text-gray-500 ml-2">Pending ({actionQueue.length})</span>
                </h2>
            </div>

            <div class="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden min-h-[400px]">
                {#if actionQueue.length === 0}
                    <div class="p-8 text-center text-gray-500">No pending actions.</div>
                {:else}
                    <div class="divide-y divide-gray-700">
                        {#each actionQueue as track}
                            <div class="p-4 hover:bg-gray-750 transition-colors flex items-center justify-between gap-4">
                                <div class="min-w-0 flex-1">
                                    <div class="flex items-center gap-2 mb-1">
                                        {#if track.action_needed === 'delete'}
                                            <span class="bg-red-900/50 text-red-200 text-[10px] font-bold px-1.5 py-0.5 rounded border border-red-800 uppercase">Delete</span>
                                        {:else}
                                            <span class="bg-blue-900/50 text-blue-200 text-[10px] font-bold px-1.5 py-0.5 rounded border border-blue-800 uppercase">Upgrade</span>
                                        {/if}
                                        <span class="text-sm font-medium text-white truncate">{track.title}</span>
                                    </div>
                                    <div class="text-xs text-gray-400 truncate">{track.artist}</div>
                                    <div class="text-xs text-gray-500 mt-1">User Rating: {track.current_rating}/5</div>
                                </div>

                                <div class="flex items-center gap-2 shrink-0">
                                    <button
                                        on:click={() => overrideTrack(track.id, 'lock')}
                                        class="p-2 hover:bg-gray-700 rounded text-gray-400 hover:text-white transition-colors"
                                        title="Pardon / Lock (Keep Safe)"
                                    >
                                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
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
