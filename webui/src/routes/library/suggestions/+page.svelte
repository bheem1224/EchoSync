<script>
    import { onMount } from 'svelte';
    import apiClient from '../../../api/client';
    import { feedback } from '../../../stores/feedback';
    import { decodeSyncId } from '../../../lib/utils';

    let autoSuggestEnabled = true;
    let togglingAuto = false;

    let loadingAccounts = true;
    let loadingAudit = true;
    let loadingPending = false;

    let accounts = [];
    let auditHistory = [];
    let pendingTracks = [];

    let modalOpen = false;
    let selectedAccount = null;
    let approvingSyncIds = new Set();

    const fallbackGenres = ['pop', 'rock', 'indie', 'electronic', 'hip hop'];

    onMount(async () => {
        await Promise.all([fetchAccounts(), fetchAudit()]);
    });

    async function fetchAccounts() {
        loadingAccounts = true;
        try {
            const response = await apiClient.get('/suggestions/accounts');
            accounts = (response.data?.accounts || []).map((account) => ({
                ...account,
                normalizedGenres: normalizeGenres(account)
            }));
        } catch (error) {
            console.error('Failed to fetch suggestion accounts:', error);
            feedback.addToast('Failed to load suggestion accounts', 'error');
            accounts = [];
        } finally {
            loadingAccounts = false;
        }
    }

    async function fetchAudit() {
        loadingAudit = true;
        try {
            const response = await apiClient.get('/suggestions/audit');
            auditHistory = response.data?.audit_history || [];
        } catch (error) {
            console.error('Failed to load suggestion audit log:', error);
            feedback.addToast('Failed to load audit log', 'error');
            auditHistory = [];
        } finally {
            loadingAudit = false;
        }
    }

    function normalizeGenres(account) {
        const source = account?.taste_profile?.top_genres;

        if (!Array.isArray(source) || source.length === 0) {
            return fallbackGenres.slice(0, 3).map((name, index) => ({
                name,
                score: 75 - index * 15
            }));
        }

        return source.slice(0, 5).map((genre, index) => {
            if (typeof genre === 'string') {
                return {
                    name: genre,
                    score: 75 - index * 12
                };
            }

            const name =
                genre.name ||
                genre.genre ||
                genre.label ||
                `genre-${index + 1}`;

            const rawScore =
                genre.score ??
                genre.weight ??
                genre.percentage ??
                genre.percent ??
                genre.count ??
                0;

            let score = Number(rawScore) || 0;
            if (score <= 1) {
                score *= 100;
            }
            score = Math.max(8, Math.min(100, score));

            return { name, score };
        });
    }

    function normalizeScore(rawValue) {
        let score = Number(rawValue ?? 0);
        if (!Number.isFinite(score)) {
            score = 0;
        }

        if (score > 10) {
            score = score / 10;
        } else if (score <= 5 && score > 0) {
            score = score * 2;
        }

        score = Math.max(0, Math.min(10, score));
        return Number(score.toFixed(1));
    }

    function normalizePendingTrack(item, index) {
        const nestedTrack = item?.track || item?.track_data || item?.track_payload || {};
        const rawSyncId = nestedTrack.sync_id || item?.sync_id || item?.id;
        const readableFromSyncId = decodeSyncId(rawSyncId);

        const title =
            nestedTrack.display_title ||
            nestedTrack.raw_title ||
            nestedTrack.title ||
            item?.track_name ||
            item?.title ||
            readableFromSyncId ||
            `Track ${index + 1}`;

        const artist =
            nestedTrack.artist_name ||
            nestedTrack.artist ||
            (Array.isArray(nestedTrack.artists) ? nestedTrack.artists.join(', ') : null) ||
            item?.artist ||
            'Unknown Artist';

        const score = normalizeScore(
            item?.matching_score ??
            item?.score ??
            item?.user_rating ??
            nestedTrack?.score
        );

        const syncId =
            rawSyncId ||
            `${selectedAccount?.id || 'acct'}-${index}-${Date.now()}`;

        const payload = {
            ...nestedTrack,
            sync_id: syncId,
            raw_title: nestedTrack.raw_title || nestedTrack.display_title || nestedTrack.title || title,
            display_title: nestedTrack.display_title || nestedTrack.title || title,
            artist_name: nestedTrack.artist_name || nestedTrack.artist || artist,
            album_title: nestedTrack.album_title || nestedTrack.album || item?.album || 'Unknown Album'
        };

        return {
            sync_id: syncId,
            title,
            artist,
            score,
            payload
        };
    }

    async function openAccount(account) {
        selectedAccount = account;
        modalOpen = true;
        await fetchPending(account.id);
    }

    async function fetchPending(accountId) {
        loadingPending = true;
        pendingTracks = [];

        try {
            const response = await apiClient.get(`/suggestions/pending/${accountId}`);
            const tracks = response.data?.pending_tracks || [];
            pendingTracks = tracks.map((item, index) => normalizePendingTrack(item, index));
        } catch (error) {
            console.error('Failed to fetch pending suggestions:', error);
            feedback.addToast('Failed to load pending suggestions', 'error');
            pendingTracks = [];
        } finally {
            loadingPending = false;
        }
    }

    async function updateAutoToggle(event) {
        const next = event.currentTarget.checked;
        const previous = autoSuggestEnabled;

        autoSuggestEnabled = next;
        togglingAuto = true;

        try {
            const response = await apiClient.post('/suggestions/toggle-auto', {
                enabled: next
            });
            autoSuggestEnabled = !!response.data?.auto_job_enabled;
            feedback.addToast(
                autoSuggestEnabled
                    ? 'Auto-Suggest enabled'
                    : 'Auto-Suggest disabled; manual approvals required',
                'success'
            );
        } catch (error) {
            console.error('Failed to update auto-suggest toggle:', error);
            autoSuggestEnabled = previous;
            feedback.addToast('Failed to update auto-suggest setting', 'error');
        } finally {
            togglingAuto = false;
        }
    }

    async function approveTrack(track) {
        if (!selectedAccount || approvingSyncIds.has(track.sync_id)) {
            return;
        }

        approvingSyncIds = new Set([...approvingSyncIds, track.sync_id]);

        try {
            await apiClient.post('/suggestions/approve', {
                account_id: selectedAccount.id,
                track: track.payload,
                playlist_name: `Suggestions for ${selectedAccount.name || 'User'}`
            });

            pendingTracks = pendingTracks.filter((item) => item.sync_id !== track.sync_id);
            feedback.addToast(`Queued ${track.title} for download and suggestion`, 'success');
            await fetchAudit();
        } catch (error) {
            console.error('Failed to approve suggestion:', error);
            feedback.addToast(`Failed to approve ${track.title}`, 'error');
        } finally {
            const updated = new Set(approvingSyncIds);
            updated.delete(track.sync_id);
            approvingSyncIds = updated;
        }
    }

    function closeModal() {
        modalOpen = false;
        selectedAccount = null;
        pendingTracks = [];
    }

    function formatDate(value) {
        if (!value) {
            return 'N/A';
        }

        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) {
            return value;
        }

        return parsed.toLocaleString();
    }

    $: selectedGenres = selectedAccount?.normalizedGenres || [];
    $: selectedTopGenreScore = Math.max(1, ...selectedGenres.map((genre) => genre.score || 0));
</script>

<svelte:head>
    <title>Suggestion Engine Dashboard • Echosync</title>
</svelte:head>

<svelte:window
    on:keydown={(event) => {
        if (event.key === 'Escape' && modalOpen) {
            closeModal();
        }
    }}
/>

<section class="mx-auto w-full max-w-7xl flex flex-col h-full min-h-0 text-slate-100" style="font-family: 'Space Grotesk', 'Segoe UI', sans-serif;">
    <header class="relative overflow-hidden rounded-3xl border border-teal-300/20 bg-gradient-to-br from-slate-950 via-cyan-950/60 to-emerald-950/40 p-6 shadow-[0_20px_55px_rgba(2,132,199,0.25)] md:p-8">
        <div class="pointer-events-none absolute -right-16 top-4 h-44 w-44 rounded-full bg-cyan-400/20 blur-3xl"></div>
        <div class="pointer-events-none absolute -left-14 bottom-0 h-36 w-36 rounded-full bg-emerald-300/15 blur-3xl"></div>

        <div class="relative flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div class="space-y-2">
                <p class="text-xs font-semibold uppercase tracking-[0.25em] text-cyan-200/70">Library Intelligence</p>
                <h1 class="text-3xl font-black leading-tight text-white md:text-4xl">Suggestion Engine Dashboard</h1>
                <p class="max-w-2xl text-sm text-slate-300 md:text-base">
                    When Auto-Suggest is off, you must manually approve recommendations for each user.
                </p>
            </div>

            <label class="inline-flex min-w-[260px] items-center justify-between gap-4 rounded-2xl border border-cyan-300/25 bg-slate-900/50 px-5 py-4 backdrop-blur-sm">
                <div>
                    <p class="text-xs uppercase tracking-[0.2em] text-cyan-200/70">Master Toggle</p>
                    <p class="text-sm font-semibold text-white">Auto-Suggest {autoSuggestEnabled ? 'On' : 'Off'}</p>
                </div>
                <span class="relative inline-flex h-8 w-14 items-center">
                    <input
                        class="peer sr-only"
                        type="checkbox"
                        checked={autoSuggestEnabled}
                        disabled={togglingAuto}
                        on:change={updateAutoToggle}
                    />
                    <span class="absolute inset-0 rounded-full bg-slate-700 transition peer-checked:bg-emerald-500"></span>
                    <span class="absolute left-1 h-6 w-6 rounded-full bg-white shadow transition-transform peer-checked:translate-x-6"></span>
                </span>
            </label>
        </div>
    </header>

    <div class="flex-1 min-h-0 overflow-y-auto space-y-8 pt-2 pb-4">
    <section class="space-y-4">
        <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-white md:text-2xl">Managed Accounts</h2>
            <button
                class="rounded-xl border border-cyan-300/20 bg-slate-900/50 px-4 py-2 text-sm font-semibold text-cyan-100 transition hover:border-cyan-200/40 hover:bg-slate-800/70"
                on:click={fetchAccounts}
            >
                Refresh Accounts
            </button>
        </div>

        {#if loadingAccounts}
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {#each Array(6) as _, i}
                    <div class="h-44 animate-pulse rounded-2xl border border-slate-700 bg-slate-900/50" aria-hidden="true"></div>
                {/each}
            </div>
        {:else if accounts.length === 0}
            <div class="rounded-2xl border border-amber-300/20 bg-amber-950/20 p-6 text-amber-100">
                No managed accounts were returned by the suggestions API.
            </div>
        {:else}
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {#each accounts as account}
                    <button
                        class="group rounded-2xl border border-slate-700 bg-slate-900/60 p-5 text-left transition hover:-translate-y-1 hover:border-cyan-300/45 hover:bg-slate-900"
                        on:click={() => openAccount(account)}
                    >
                        <div class="mb-4 flex items-start justify-between">
                            <div>
                                <p class="text-lg font-bold text-white">{account.name || 'Unknown Account'}</p>
                                <p class="text-xs uppercase tracking-[0.2em] text-slate-400">Account ID: {account.id}</p>
                            </div>
                            <span class="rounded-full px-3 py-1 text-xs font-semibold {account.is_active ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-700 text-slate-300'}">
                                {account.is_active ? 'Active' : 'Inactive'}
                            </span>
                        </div>

                        <p class="mb-3 text-sm text-slate-300">
                            Approved suggestions: {account?.taste_profile?.total_suggestions ?? 0}
                        </p>

                        <div class="flex flex-wrap gap-2">
                            {#each account.normalizedGenres as genre}
                                <span class="rounded-full border border-cyan-300/25 bg-cyan-400/10 px-3 py-1 text-xs font-medium text-cyan-100">
                                    {genre.name}
                                </span>
                            {/each}
                        </div>
                    </button>
                {/each}
            </div>
        {/if}
    </section>

    <section class="space-y-4 rounded-2xl border border-slate-700 bg-slate-950/55 p-5 md:p-6">
        <div class="flex items-center justify-between gap-3">
            <div>
                <p class="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-200/70">Audit Log</p>
                <h3 class="text-xl font-bold text-white">Successfully Suggested Tracks</h3>
            </div>
            <button
                class="rounded-xl border border-cyan-300/20 bg-slate-900/60 px-4 py-2 text-sm font-semibold text-cyan-100 transition hover:border-cyan-200/40 hover:bg-slate-800/70"
                on:click={fetchAudit}
            >
                Refresh Log
            </button>
        </div>

        {#if loadingAudit}
            <div class="rounded-xl border border-slate-700 bg-slate-900/70 p-6 text-sm text-slate-300">Loading audit records...</div>
        {:else if auditHistory.length === 0}
            <div class="rounded-xl border border-slate-700 bg-slate-900/70 p-6 text-sm text-slate-300">No approved suggestions found yet.</div>
        {:else}
            <div class="overflow-x-auto rounded-xl border border-slate-700">
                <table class="min-w-full divide-y divide-slate-700 bg-slate-900/70 text-sm">
                    <thead class="bg-slate-900/95 text-left text-xs uppercase tracking-[0.14em] text-slate-300">
                        <tr>
                            <th class="px-4 py-3">Track ID</th>
                            <th class="px-4 py-3">Status</th>
                            <th class="px-4 py-3">Queued At</th>
                            <th class="px-4 py-3">Updated At</th>
                            <th class="px-4 py-3">Retries</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-800 text-slate-200">
                        {#each auditHistory as row}
                            <tr class="hover:bg-slate-800/45">
                                <td class="px-4 py-3 font-medium text-cyan-100">{decodeSyncId(row.sync_id) || row.id}</td>
                                <td class="px-4 py-3">
                                    <span class="rounded-full px-2.5 py-1 text-xs font-semibold {row.status === 'completed' ? 'bg-emerald-500/15 text-emerald-300' : row.status === 'failed' ? 'bg-rose-500/20 text-rose-300' : 'bg-cyan-500/20 text-cyan-200'}">
                                        {row.status || 'unknown'}
                                    </span>
                                </td>
                                <td class="px-4 py-3 text-slate-300">{formatDate(row.created_at)}</td>
                                <td class="px-4 py-3 text-slate-300">{formatDate(row.updated_at)}</td>
                                <td class="px-4 py-3 text-slate-300">{row.retry_count ?? 0}</td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </section>
    </div>
</section>

{#if modalOpen && selectedAccount}
    <div
        class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/80 p-4 backdrop-blur-sm md:items-center"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        on:click={(event) => {
            if (event.target === event.currentTarget) {
                closeModal();
            }
        }}
        on:keydown={(event) => {
            if (event.key === 'Escape') {
                closeModal();
            }
        }}
    >
        <div class="max-h-[92vh] w-full max-w-4xl overflow-hidden rounded-3xl border border-cyan-300/25 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-950 shadow-[0_20px_80px_rgba(8,145,178,0.35)]">
            <header class="flex items-center justify-between border-b border-slate-700/90 px-6 py-4">
                <div>
                    <p class="text-xs uppercase tracking-[0.2em] text-cyan-200/70">Profile & Approval</p>
                    <h3 class="text-2xl font-black text-white">{selectedAccount.name}</h3>
                </div>
                <button
                    class="rounded-full border border-slate-600 p-2 text-slate-200 transition hover:border-cyan-300 hover:text-cyan-200"
                    on:click={closeModal}
                    aria-label="Close profile drawer"
                >
                    <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 6l12 12M6 18L18 6"></path>
                    </svg>
                </button>
            </header>

            <div class="grid max-h-[calc(92vh-74px)] grid-cols-1 gap-6 overflow-y-auto p-6 lg:grid-cols-5">
                <section class="space-y-4 rounded-2xl border border-cyan-300/20 bg-slate-900/60 p-4 lg:col-span-2">
                    <div class="flex items-center justify-between">
                        <h4 class="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-100/80">Taste Profile</h4>
                        <span class="text-xs text-slate-400">Top genres</span>
                    </div>

                    {#if selectedGenres.length === 0}
                        <p class="text-sm text-slate-300">No taste profile data is available for this account yet.</p>
                    {:else}
                        <div class="space-y-3">
                            {#each selectedGenres as genre}
                                <div class="space-y-1.5">
                                    <div class="flex items-center justify-between text-xs text-slate-300">
                                        <span class="font-semibold text-white">{genre.name}</span>
                                        <span>{Math.round((genre.score / selectedTopGenreScore) * 100)}%</span>
                                    </div>
                                    <div class="h-2 rounded-full bg-slate-800">
                                        <div
                                            class="h-2 rounded-full bg-gradient-to-r from-cyan-400 to-emerald-400"
                                            style="width: {Math.max(8, Math.round((genre.score / selectedTopGenreScore) * 100))}%"
                                        ></div>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </section>

                <section class="rounded-2xl border border-slate-700 bg-slate-900/50 p-4 lg:col-span-3">
                    <div class="mb-4 flex items-center justify-between">
                        <h4 class="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-100/80">Pending Queue</h4>
                        <button
                            class="rounded-lg border border-cyan-300/20 px-3 py-1.5 text-xs font-semibold text-cyan-100 transition hover:border-cyan-200/40"
                            on:click={() => fetchPending(selectedAccount.id)}
                        >
                            Refresh Queue
                        </button>
                    </div>

                    {#if loadingPending}
                        <p class="text-sm text-slate-300">Loading recommendations...</p>
                    {:else if pendingTracks.length === 0}
                        <div class="rounded-xl border border-slate-700 bg-slate-900/70 p-4 text-sm text-slate-300">
                            No pending recommendations for this account.
                        </div>
                    {:else}
                        <div class="space-y-3">
                            {#each pendingTracks as track}
                                <article class="rounded-xl border border-slate-700 bg-slate-900/80 p-3">
                                    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                        <div class="space-y-1">
                                            <p class="text-sm font-semibold text-white">{track.title}</p>
                                            <p class="text-xs text-slate-400">{track.artist}</p>
                                            <p class="text-xs text-cyan-200">Matching Engine score: {track.score}/10</p>
                                        </div>

                                        <button
                                            class="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
                                            on:click={() => approveTrack(track)}
                                            disabled={approvingSyncIds.has(track.sync_id)}
                                        >
                                            {approvingSyncIds.has(track.sync_id) ? 'Approving...' : 'Download & Suggest'}
                                        </button>
                                    </div>
                                </article>
                            {/each}
                        </div>
                    {/if}
                </section>
            </div>
        </div>
    </div>
{/if}
