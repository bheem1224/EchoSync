<script>
  import { fly, fade } from 'svelte/transition';
  import apiClient from '../../api/client';

  let {
    isOpen = false,
    track = null,
    onClose = () => {}
  } = $props();

  let loading = $state(false);
  let error = $state(null);
  let diagnosticData = $state(null);

  $effect(() => {
    if (isOpen && track) {
      fetchDiagnostics(track);
    } else {
      diagnosticData = null;
      error = null;
    }
  });

  function parseDurationToMs(dur) {
    if (!dur) return 0;
    if (typeof dur === 'number') return dur;
    const parts = String(dur).split(':').map(Number);
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return (parts[0] * 60 + parts[1]) * 1000;
    }
    return 0;
  }

  async function fetchDiagnostics(t) {
    loading = true;
    error = null;
    try {
      const durationMs = t.duration_ms || parseDurationToMs(t.duration) || 0;
      const payload = {
        title: t.title || '',
        artist: t.artist || '',
        duration_ms: durationMs,
        album: t.album || null
      };

      let resp;
      try {
        resp = await apiClient.post('/core/playlists/match-diagnostics', payload);
      } catch (clientErr) {
        // Fallback to direct fetch
        const direct = await fetch('/api/v1/core/playlists/match-diagnostics', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!direct.ok) {
          throw new Error(`Failed to fetch diagnostics: ${direct.statusText}`);
        }
        resp = { data: await direct.json() };
      }
      diagnosticData = resp.data;
    } catch (err) {
      console.error('Match diagnostics fetch error:', err);
      error = err.message || 'Failed to retrieve match diagnostics';
    } finally {
      loading = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Escape' && isOpen) {
      onClose();
    }
  }

  function formatPercent(val) {
    if (val === null || val === undefined) return '0%';
    const num = typeof val === 'number' ? val : parseFloat(val);
    if (isNaN(num)) return '0%';
    return num <= 1.0 ? `${Math.round(num * 100)}%` : `${num.toFixed(1)}%`;
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 transition-opacity"
    onclick={onClose}
    transition:fade={{ duration: 180 }}
    aria-hidden="true"
  ></div>

  <!-- Slide-out Drawer Panel -->
  <aside
    class="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] bg-slate-900 text-slate-100 border-l border-slate-700/80 shadow-2xl flex flex-col overflow-hidden"
    transition:fly={{ x: 480, duration: 240 }}
    aria-label="Playlist Track Match Diagnostics"
  >
    <!-- Header -->
    <div class="p-4 border-b border-slate-800 bg-slate-900/95 flex items-start justify-between gap-3 select-none">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1 flex-wrap">
          <span class="text-xs font-semibold px-2 py-0.5 rounded tracking-wide uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            Match Diagnostics
          </span>
          {#if track}
            {@const isFound = track.library_match === 'Found' || (track.library_match && track.library_match.includes('Found'))}
            <span class="text-xs font-semibold px-2 py-0.5 rounded border {isFound ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/15 text-rose-400 border-rose-500/30'}">
              {isFound ? 'Found' : 'Not Found'}
            </span>
            {#if track.duration}
              <span class="text-xs text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded font-mono">
                {track.duration}
              </span>
            {/if}
          {/if}
        </div>
        <h2 class="text-base font-bold text-white truncate" title={track?.title || 'Unknown Track'}>
          {track?.title || 'Unknown Track'}
        </h2>
        <p class="text-xs text-slate-400 truncate" title={track?.artist || 'Unknown Artist'}>
          {track?.artist || 'Unknown Artist'}
        </p>
      </div>

      <!-- Close Button -->
      <button
        type="button"
        class="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
        onclick={onClose}
        aria-label="Close Drawer"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
      <!-- Query Details Card -->
      <div class="bg-slate-800/60 rounded-xl p-3 border border-slate-700/60 space-y-2">
        <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Query Details
        </div>
        <div class="grid grid-cols-2 gap-2 text-slate-300">
          <div>
            <span class="text-slate-500 block text-[10px]">Title</span>
            <span class="font-medium text-white truncate block">{track?.title || '–'}</span>
          </div>
          <div>
            <span class="text-slate-500 block text-[10px]">Artist</span>
            <span class="font-medium text-white truncate block">{track?.artist || '–'}</span>
          </div>
          <div>
            <span class="text-slate-500 block text-[10px]">Expected Duration</span>
            <span class="font-mono text-white block">
              {track?.duration || (track?.duration_ms ? `${(track.duration_ms / 1000).toFixed(1)}s` : '–')}
            </span>
          </div>
          <div>
            <span class="text-slate-500 block text-[10px]">Album (Source)</span>
            <span class="font-medium text-white truncate block">{track?.album || '–'}</span>
          </div>
        </div>
      </div>

      <!-- Retrieval Status -->
      <div class="flex items-center justify-between px-1 text-slate-400 text-xs">
        <span>Database Candidates Located:</span>
        {#if loading}
          <span class="text-indigo-400 animate-pulse font-medium">Querying library…</span>
        {:else if diagnosticData}
          <span class="font-bold text-teal-400 font-mono">
            {diagnosticData.candidates_retrieved_count} candidate{diagnosticData.candidates_retrieved_count === 1 ? '' : 's'}
          </span>
        {:else}
          <span>–</span>
        {/if}
      </div>

      {#if loading}
        <!-- Loading Skeleton -->
        <div class="space-y-3 pt-2">
          {#each [1, 2, 3] as _}
            <div class="bg-slate-800/40 rounded-xl p-3 border border-slate-800 animate-pulse space-y-2">
              <div class="h-4 bg-slate-700/60 rounded w-3/4"></div>
              <div class="h-3 bg-slate-700/40 rounded w-1/2"></div>
              <div class="h-8 bg-slate-700/20 rounded"></div>
            </div>
          {/each}
        </div>
      {:else if error}
        <div class="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300">
          <div class="font-semibold mb-1">Diagnostic Error</div>
          <div class="text-[11px] text-rose-400">{error}</div>
        </div>
      {:else if diagnosticData}
        {#if diagnosticData.candidates && diagnosticData.candidates.length > 0}
          <div class="space-y-3">
            <div class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-1">
              Evaluated Candidates ({diagnosticData.candidates.length})
            </div>

            {#each diagnosticData.candidates as cand, idx}
              {@const isWinner = diagnosticData.best_match && diagnosticData.best_match.track_sync_id === cand.track_sync_id && cand.accepted}
              {@const isVetoed = !cand.accepted && (cand.duration_delta_sec > 6.0 || (cand.rejection_reason && cand.rejection_reason.includes('Duration Delta > 6.0s')))}
              
              <div class="bg-slate-800/50 rounded-xl p-3 border transition-all {isWinner ? 'border-emerald-500/50 bg-emerald-950/10' : 'border-slate-700/60'}">
                <!-- Candidate Header -->
                <div class="flex items-start justify-between gap-2 mb-2">
                  <div class="min-w-0 flex-1">
                    <div class="font-bold text-white text-xs truncate" title={cand.title}>
                      {cand.title}
                    </div>
                    <div class="text-slate-400 text-[11px] truncate" title={cand.artist}>
                      {cand.artist}
                    </div>
                    {#if cand.album}
                      <div class="text-slate-500 text-[10px] truncate" title={cand.album}>
                        💿 {cand.album}
                      </div>
                    {/if}
                  </div>

                  <!-- Outcome Badge -->
                  <div>
                    {#if isWinner}
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                        ✓ ACCEPTED
                      </span>
                    {:else if cand.accepted}
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                        ACCEPTED
                      </span>
                    {:else if isVetoed}
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                        ⚠ VETOED
                      </span>
                    {:else}
                      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        ✕ REJECTED
                      </span>
                    {/if}
                  </div>
                </div>

                <!-- Scores Breakdown Grid -->
                <div class="grid grid-cols-4 gap-1.5 py-2 px-2 bg-slate-900/60 rounded-lg text-center mb-2 border border-slate-800">
                  <div>
                    <span class="text-[9px] text-slate-500 block uppercase">Title</span>
                    <span class="font-mono font-semibold text-slate-200">{formatPercent(cand.title_score)}</span>
                  </div>
                  <div>
                    <span class="text-[9px] text-slate-500 block uppercase">Artist</span>
                    <span class="font-mono font-semibold text-slate-200">{formatPercent(cand.artist_score)}</span>
                  </div>
                  <div>
                    <span class="text-[9px] text-slate-500 block uppercase">Duration</span>
                    <span class="font-mono font-semibold text-slate-200">{formatPercent(cand.duration_score)}</span>
                  </div>
                  <div>
                    <span class="text-[9px] text-slate-500 block uppercase">Album</span>
                    <span class="font-mono font-semibold text-slate-200">{formatPercent(cand.album_score)}</span>
                  </div>
                </div>

                <!-- Delta & Penalties Row -->
                <div class="flex items-center justify-between text-[11px] text-slate-400 mb-2 px-1">
                  <div>
                    <span>Δt:</span>
                    <span class="font-mono {cand.duration_delta_sec > 6.0 ? 'text-amber-400 font-bold' : 'text-slate-300'}">
                      {cand.duration_delta_sec > 0 ? `+${cand.duration_delta_sec}s` : `${cand.duration_delta_sec}s`}
                    </span>
                  </div>
                  <div>
                    <span>Penalties:</span>
                    {#if cand.penalties && Object.keys(cand.penalties).length > 0}
                      <span class="text-rose-400 font-mono">
                        {Object.entries(cand.penalties).map(([k, v]) => `${k.replace('_penalty', '')}: -${v}`).join(', ')}
                      </span>
                    {:else}
                      <span class="text-emerald-400 font-mono">0.0</span>
                    {/if}
                  </div>
                </div>

                <!-- Composite Score vs Threshold -->
                <div class="pt-1 border-t border-slate-700/40">
                  <div class="flex items-center justify-between text-[11px] mb-1">
                    <span class="text-slate-400">Composite Score</span>
                    <span class="font-mono font-bold {cand.accepted ? 'text-emerald-400' : 'text-slate-300'}">
                      {cand.composite_score.toFixed(1)}% <span class="text-slate-500 font-normal">/ {diagnosticData.winning_threshold}% req</span>
                    </span>
                  </div>
                  <div class="h-1.5 w-full bg-slate-700/60 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-300 {cand.accepted ? 'bg-emerald-500' : isVetoed ? 'bg-amber-500' : 'bg-slate-500'}"
                      style="width: {Math.min(100, Math.max(0, cand.composite_score))}%"
                    ></div>
                  </div>
                </div>

                <!-- Rejection Reason if any -->
                {#if cand.rejection_reason}
                  <div class="mt-2 text-[10px] text-rose-400/90 bg-rose-950/20 px-2 py-1 rounded border border-rose-900/30">
                    {cand.rejection_reason}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {:else}
          <!-- Zero Candidates State -->
          <div class="bg-slate-800/40 rounded-xl p-4 border border-slate-800 text-center space-y-2 py-6">
            <div class="text-2xl">🔍</div>
            <div class="font-semibold text-slate-300">No Candidates Located</div>
            <p class="text-slate-400 text-[11px] max-w-xs mx-auto leading-relaxed">
              No matching track candidates were found in the library database across Tier 1 (title + artist) and Tier 2 (title + duration) queries.
            </p>
          </div>
        {/if}
      {/if}
    </div>
  </aside>
{/if}

