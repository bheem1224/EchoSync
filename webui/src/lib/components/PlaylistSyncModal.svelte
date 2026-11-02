<script>
  import PlaylistMatchDiagnosticDrawer from './PlaylistMatchDiagnosticDrawer.svelte';

  let {
    isOpen = false,
    title = 'Playlist Sync Analysis',
    sourceProvider = '',
    targetProvider = '',
    analysisResult = null,
    qualityProfiles = [],
    selectedQuality = $bindable(''),
    loading = false,
    downloading = false,
    onClose = () => {},
    onRunAnalysis = () => {},
    onConfirmSync = () => {},
    onDownloadMissing = () => {},
    onSelectTrack = null,
  } = $props();

  let selectedTrack = $state(null);
  let isDiagnosticsOpen = $state(false);

  function handleTrackClick(track) {
    selectedTrack = track;
    isDiagnosticsOpen = true;
    if (onSelectTrack) {
      onSelectTrack(track);
    }
  }

  function handleClose() {
    isDiagnosticsOpen = false;
    selectedTrack = null;
    onClose();
  }
</script>

{#if isOpen}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-6 bg-slate-950/80 backdrop-blur-sm"
    role="dialog"
    aria-modal="true"
  >
    <div
      class="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl flex flex-col w-full max-w-7xl h-[85vh] max-h-[85vh] overflow-hidden"
    >
      <!-- Modal Header (Fixed height, shrink-0) -->
      <div class="p-6 border-b border-slate-800 shrink-0 flex items-center justify-between">
        <div>
          <span class="text-xs font-semibold tracking-wider uppercase text-emerald-400">Playlist Sync</span>
          <h2 class="text-xl font-bold text-white mt-0.5">{title}</h2>
          {#if sourceProvider || targetProvider}
            <p class="text-xs text-slate-400 mt-1">
              Source: <span class="text-slate-200 font-medium">{sourceProvider}</span> → Target: <span class="text-slate-200 font-medium">{targetProvider}</span>
            </p>
          {/if}
        </div>

        <div class="flex items-center gap-4">
          <!-- Target Quality Dropdown -->
          <div class="flex items-center gap-2">
            <label for="quality-select" class="text-xs text-slate-400 whitespace-nowrap">Target Quality:</label>
            <select
              id="quality-select"
              bind:value={selectedQuality}
              class="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
            >
              {#if qualityProfiles.length === 0}
                <option value="">Default (FLAC/Lossless)</option>
              {:else}
                {#each qualityProfiles as profile}
                  <option value={profile.name || profile.id}>{profile.name || profile.id}</option>
                {/each}
              {/if}
            </select>
          </div>

          <!-- Action Buttons -->
          <button
            type="button"
            class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors disabled:opacity-50"
            onclick={onRunAnalysis}
            disabled={loading}
          >
            {loading ? 'Analyzing…' : 'Re-run Analysis'}
          </button>

          <button
            type="button"
            class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition-colors disabled:opacity-50"
            onclick={onConfirmSync}
            disabled={loading || !analysisResult}
          >
            Sync Playlist
          </button>

          {#if (analysisResult?.summary?.missing_tracks ?? 0) > 0}
            <button
              type="button"
              class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-50"
              onclick={onDownloadMissing}
              disabled={downloading}
            >
              {downloading ? 'Downloading…' : `Download Missing (${analysisResult?.summary?.missing_tracks})`}
            </button>
          {/if}

          <!-- Close Modal Button -->
          <button
            type="button"
            class="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors ml-2"
            onclick={handleClose}
            aria-label="Close Modal"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Dual-Pane Body Container (Takes remaining height, never overflows outer modal) -->
      <div class="flex-1 min-h-0 flex flex-row overflow-hidden">
        <!-- Left Pane: Track Table (Independent vertical scroll) -->
        <div class="flex-1 min-h-0 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-700 space-y-6">
          <!-- Summary Cards -->
          {#if analysisResult?.summary}
            <div class="grid grid-cols-4 gap-4">
              <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span class="text-xs text-slate-400 block font-medium">Total Tracks</span>
                <span class="text-xl font-bold text-white mt-1 block">{analysisResult.summary.total_tracks ?? 0}</span>
              </div>
              <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span class="text-xs text-slate-400 block font-medium">Found in Library</span>
                <span class="text-xl font-bold text-emerald-400 mt-1 block">{analysisResult.summary.found_in_library ?? 0}</span>
              </div>
              <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span class="text-xs text-slate-400 block font-medium">Missing</span>
                <span class="text-xl font-bold text-rose-400 mt-1 block">{analysisResult.summary.missing_tracks ?? 0}</span>
              </div>
              <div class="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
                <span class="text-xs text-slate-400 block font-medium">Target Quality</span>
                <span class="text-sm font-semibold text-indigo-300 mt-1 block truncate">{selectedQuality || 'Any'}</span>
              </div>
            </div>
          {/if}

          <!-- Tracks Table (#, Track, Artist, Duration, Match Quality, Download Status) -->
          <div class="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-inner">
            <div class="grid grid-cols-[40px_1fr_1fr_90px_130px_110px] items-center gap-3 px-4 py-3 bg-slate-800/80 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800">
              <span class="text-center">#</span>
              <span>Track</span>
              <span>Artist</span>
              <span>Duration</span>
              <span class="text-center">Match Quality</span>
              <span class="text-center">Download Status</span>
            </div>

            {#if loading}
              <div class="py-12 text-center text-sm text-slate-400">Analyzing playlist tracks against local library…</div>
            {:else if analysisResult?.tracks?.length}
              <div class="divide-y divide-slate-800/60">
                {#each analysisResult.tracks as track, idx}
                  {@const isFound = track.status === 'found' || track.library_match === 'Found' || (track.library_match && !track.library_match.includes('missing'))}
                  {@const isSelected = selectedTrack === track && isDiagnosticsOpen}
                  <button
                    type="button"
                    class="w-full grid grid-cols-[40px_1fr_1fr_90px_130px_110px] items-center gap-3 px-4 py-3 text-left text-xs transition-colors hover:bg-slate-800/50 {isSelected ? 'bg-indigo-950/40 ring-1 ring-inset ring-indigo-500/50' : ''}"
                    onclick={() => handleTrackClick(track)}
                  >
                    <span class="text-slate-500 font-mono text-center">{idx + 1}</span>
                    <span class="font-medium text-slate-200 truncate" title={track.title}>{track.title}</span>
                    <span class="text-slate-400 truncate" title={track.artist}>{track.artist}</span>
                    <span class="font-mono text-slate-400">{track.duration || '–'}</span>
                    <span class="text-center">
                      <span class="inline-block px-2 py-0.5 rounded text-[11px] font-semibold {isFound ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950/80 text-rose-400 border border-rose-800/50'}">
                        {track.library_match || (isFound ? 'Found' : 'Missing')}
                      </span>
                    </span>
                    <span class="text-center text-slate-400">{track.download_status || '–'}</span>
                  </button>
                {/each}
              </div>
            {:else}
              <div class="py-12 text-center text-sm text-slate-500">No tracks available in analysis result.</div>
            {/if}
          </div>
        </div>

        <!-- Right Pane: Diagnostic Sidebar (Docked, independent vertical scroll) -->
        {#if isDiagnosticsOpen && selectedTrack}
          <PlaylistMatchDiagnosticDrawer
            isOpen={isDiagnosticsOpen}
            track={selectedTrack}
            onClose={() => { isDiagnosticsOpen = false; }}
          />
        {/if}
      </div>
    </div>
  </div>
{/if}

