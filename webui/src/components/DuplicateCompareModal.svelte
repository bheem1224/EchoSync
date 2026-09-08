<script>
  import { createEventDispatcher } from 'svelte';
  import apiClient from '../api/client';

  export let item = null;
  export let isOpen = false;

  const dispatch = createEventDispatcher();

  let isSwapping = false;
  let isResolving = false;
  let isVetoing = false;
  let localWinner = null;
  let localLoser = null;

  $: if (item) {
    localWinner = item.winner_track ? { ...item.winner_track } : null;
    localLoser = item.loser_track ? { ...item.loser_track } : null;
  }

  function close() {
    dispatch('close');
  }

  function formatBitrate(bps) {
    if (!bps) return '—';
    if (bps >= 1000) return `${Math.round(bps / 1000)} kbps`;
    return `${bps} bps`;
  }

  function formatSampleRate(hz) {
    if (!hz) return '—';
    if (hz >= 1000) return `${(hz / 1000).toFixed(1)} kHz`;
    return `${hz} Hz`;
  }

  function formatDuration(ms) {
    if (!ms) return '—';
    const totalSec = Math.round(ms > 10000 ? ms / 1000 : ms);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec < 10 ? '0' : ''}${sec}`;
  }

  function formatBadge(track) {
    if (!track) return 'UNKNOWN';
    const fmt = (track.format || 'AUDIO').toUpperCase();
    const br = track.bitrate ? ` ${Math.round(track.bitrate / 1000)}k` : '';
    return `${fmt}${br}`;
  }

  async function handleSwap() {
    if (!localWinner || !localLoser || isSwapping) return;
    isSwapping = true;
    try {
      // Immediate local swap for zero-latency UX
      const temp = localWinner;
      localWinner = localLoser;
      localLoser = temp;

      if (item?.sync_id) {
        await apiClient.post(`/system/manager/suggestions/${item.sync_id}/swap`);
      }
    } catch (err) {
      console.error('Failed to persist swap on backend:', err);
    } finally {
      isSwapping = false;
    }
  }

  async function handleApprove() {
    if (!localWinner || !localLoser || isResolving) return;
    isResolving = true;
    try {
      await apiClient.post('/system/manager/conflicts/resolve', {
        keep_id: localWinner.id,
        delete_ids: [localLoser.id],
        sync_id: item?.sync_id,
      });
      dispatch('resolved', {
        sync_id: item?.sync_id,
        action: 'approved',
        keep_id: localWinner.id,
        delete_id: localLoser.id,
      });
      close();
    } catch (err) {
      console.error('Failed to resolve duplicate conflict:', err);
      alert('Failed to resolve duplicate conflict. Please try again.');
    } finally {
      isResolving = false;
    }
  }

  async function handleVeto() {
    if (!item?.sync_id || isVetoing) return;
    isVetoing = true;
    try {
      await apiClient.post('/system/manager/veto', {
        sync_id: item.sync_id,
        reason: 'User kept both duplicates via compare modal',
      });
      dispatch('resolved', {
        sync_id: item.sync_id,
        action: 'vetoed',
      });
      close();
    } catch (err) {
      console.error('Failed to veto duplicate suggestion:', err);
      alert('Failed to veto suggestion.');
    } finally {
      isVetoing = false;
    }
  }
</script>

{#if isOpen && item}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
    <!-- Modal Container -->
    <div class="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-[#0f1318] border border-white/10 rounded-xl shadow-2xl overflow-hidden">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/[0.02]">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-primary/10 text-primary">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </div>
          <div>
            <h2 class="text-base font-bold text-white tracking-wide">Duplicate Track Comparison</h2>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-xs text-muted">Review candidate tracks side-by-side</span>
              {#if item.comparison_reason}
                <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  {item.comparison_reason}
                </span>
              {/if}
            </div>
          </div>
        </div>
        <button
          class="p-1.5 rounded-lg text-muted hover:text-white hover:bg-white/10 transition-colors"
          on:click={close}
          title="Close modal"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Content Scrollable -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6 custom-scrollbar">
        <!-- Side by Side Preview Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Left: Keep Track (Winner) -->
          <div class="flex flex-col p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 shadow-inner">
            <div class="flex items-center justify-between mb-3">
              <span class="inline-flex items-center gap-1.5 text-xs font-black uppercase tracking-wider px-2.5 py-1 rounded-md bg-emerald-500/25 text-emerald-300 border border-emerald-500/40">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                Keep Track (Winner)
              </span>
              <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                {formatBadge(localWinner)}
              </span>
            </div>

            <div class="space-y-1">
              <h3 class="text-base font-bold text-white truncate" title={localWinner?.title || 'Unknown'}>
                {localWinner?.title || 'Unknown Title'}
              </h3>
              <p class="text-xs text-muted truncate" title={localWinner?.artist || 'Unknown'}>
                {localWinner?.artist || 'Unknown Artist'} &bull; {localWinner?.album || 'Unknown Album'}
              </p>
            </div>

            <!-- Embedded Audio Player Winner -->
            <div class="mt-4 pt-3 border-t border-emerald-500/20">
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-emerald-400 mb-1.5">
                Audio Preview (Winner)
              </label>
              {#if localWinner?.id}
                <audio
                  controls
                  preload="metadata"
                  class="w-full h-8 rounded bg-black/40 outline-none"
                  src="/api/v1/core/library/tracks/{localWinner.id}/stream"
                >
                  Your browser does not support HTML5 audio.
                </audio>
              {:else}
                <div class="text-xs text-muted italic">Streaming preview unavailable</div>
              {/if}
            </div>
          </div>

          <!-- Right: Delete Track (Loser) -->
          <div class="flex flex-col p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 shadow-inner">
            <div class="flex items-center justify-between mb-3">
              <span class="inline-flex items-center gap-1.5 text-xs font-black uppercase tracking-wider px-2.5 py-1 rounded-md bg-rose-500/25 text-rose-300 border border-rose-500/40">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete Track (Loser)
              </span>
              <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                {formatBadge(localLoser)}
              </span>
            </div>

            <div class="space-y-1">
              <h3 class="text-base font-bold text-white truncate" title={localLoser?.title || 'Unknown'}>
                {localLoser?.title || 'Unknown Title'}
              </h3>
              <p class="text-xs text-muted truncate" title={localLoser?.artist || 'Unknown'}>
                {localLoser?.artist || 'Unknown Artist'} &bull; {localLoser?.album || 'Unknown Album'}
              </p>
            </div>

            <!-- Embedded Audio Player Loser -->
            <div class="mt-4 pt-3 border-t border-rose-500/20">
              <label class="block text-[11px] font-semibold uppercase tracking-wider text-rose-400 mb-1.5">
                Audio Preview (Loser)
              </label>
              {#if localLoser?.id}
                <audio
                  controls
                  preload="metadata"
                  class="w-full h-8 rounded bg-black/40 outline-none"
                  src="/api/v1/core/library/tracks/{localLoser.id}/stream"
                >
                  Your browser does not support HTML5 audio.
                </audio>
              {:else}
                <div class="text-xs text-muted italic">Streaming preview unavailable</div>
              {/if}
            </div>
          </div>
        </div>

        <!-- Metadata Comparison Table -->
        <div class="border border-white/10 rounded-xl overflow-hidden bg-black/30">
          <div class="px-4 py-2.5 bg-white/[0.03] border-b border-white/10 flex items-center justify-between">
            <span class="text-xs font-bold uppercase tracking-wider text-white/80">Detailed Technical Comparison</span>
            <button
              on:click={handleSwap}
              disabled={isSwapping}
              class="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold bg-white/10 text-white hover:bg-white/20 transition-all active:scale-95 disabled:opacity-50"
            >
              <svg class="w-3.5 h-3.5 {isSwapping ? 'animate-spin' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
              Swap Winner / Loser
            </button>
          </div>

          <table class="w-full text-xs text-left border-collapse">
            <thead>
              <tr class="border-b border-white/10 bg-white/[0.01] text-muted">
                <th class="py-2.5 px-4 w-1/4 font-semibold">Attribute</th>
                <th class="py-2.5 px-4 w-3/8 font-semibold text-emerald-400">Keep (Winner)</th>
                <th class="py-2.5 px-4 w-3/8 font-semibold text-rose-400">Delete (Loser)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-2.5 px-4 font-medium text-muted">Track Title</td>
                <td class="py-2.5 px-4 text-white font-medium">{localWinner?.title || '—'}</td>
                <td class="py-2.5 px-4 text-white/80">{localLoser?.title || '—'}</td>
              </tr>
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-2.5 px-4 font-medium text-muted">Artist</td>
                <td class="py-2.5 px-4 text-white">{localWinner?.artist || '—'}</td>
                <td class="py-2.5 px-4 text-white/80">{localLoser?.artist || '—'}</td>
              </tr>
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-2.5 px-4 font-medium text-muted">Album</td>
                <td class="py-2.5 px-4 text-white">{localWinner?.album || '—'}</td>
                <td class="py-2.5 px-4 text-white/80">{localLoser?.album || '—'}</td>
              </tr>
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-2.5 px-4 font-medium text-muted">Audio Format</td>
                <td class="py-2.5 px-4">
                  <span class="font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {(localWinner?.format || '—').toUpperCase()}
                  </span>
                </td>
                <td class="py-2.5 px-4">
                  <span class="font-mono font-bold px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                    {(localLoser?.format || '—').toUpperCase()}
                  </span>
                </td>
              </tr>
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-2.5 px-4 font-medium text-muted">Bitrate</td>
                <td class="py-2.5 px-4 font-mono font-semibold text-emerald-400">
                  {formatBitrate(localWinner?.bitrate)}
                </td>
                <td class="py-2.5 px-4 font-mono text-muted">
                  {formatBitrate(localLoser?.bitrate)}
                </td>
              </tr>
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-2.5 px-4 font-medium text-muted">Sample Rate</td>
                <td class="py-2.5 px-4 font-mono text-white">
                  {formatSampleRate(localWinner?.sample_rate)}
                </td>
                <td class="py-2.5 px-4 font-mono text-muted">
                  {formatSampleRate(localLoser?.sample_rate)}
                </td>
              </tr>
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-2.5 px-4 font-medium text-muted">Duration</td>
                <td class="py-2.5 px-4 font-mono text-white">
                  {formatDuration(localWinner?.duration)}
                </td>
                <td class="py-2.5 px-4 font-mono text-muted">
                  {formatDuration(localLoser?.duration)}
                </td>
              </tr>
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-2.5 px-4 font-medium text-muted">File Path</td>
                <td class="py-2.5 px-4 font-mono text-[11px] text-white/90 break-all bg-emerald-950/10">
                  {localWinner?.file_path || '—'}
                </td>
                <td class="py-2.5 px-4 font-mono text-[11px] text-white/70 break-all bg-rose-950/10">
                  {localLoser?.file_path || '—'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Footer Action Buttons -->
      <div class="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-t border-white/10 bg-white/[0.02]">
        <div class="flex items-center gap-2">
          <button
            on:click={handleSwap}
            disabled={isSwapping || isResolving}
            class="px-4 py-2 text-xs font-bold rounded-lg border border-white/20 bg-white/5 text-white hover:bg-white/15 transition-all active:scale-95 disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
            Swap Winner/Loser
          </button>
          <button
            on:click={handleVeto}
            disabled={isVetoing || isResolving}
            class="px-4 py-2 text-xs font-bold rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 transition-all active:scale-95 disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            Veto / Keep Both
          </button>
        </div>

        <div class="flex items-center gap-2">
          <button
            on:click={close}
            class="px-4 py-2 text-xs font-bold rounded-lg border border-white/10 bg-transparent text-muted hover:text-white hover:bg-white/5 transition-all"
          >
            Cancel
          </button>
          <button
            on:click={handleApprove}
            disabled={isResolving}
            class="px-5 py-2 text-xs font-black rounded-lg bg-emerald-500 text-black hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/20 active:scale-95 disabled:opacity-50 inline-flex items-center gap-1.5"
          >
            {#if isResolving}
              <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
              </svg>
              Processing...
            {:else}
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Approve Deletion
            {/if}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes fadeIn {
    from { opacity: 0; transform: scale(0.98); }
    to { opacity: 1; transform: scale(1); }
  }
  .animate-fadeIn {
    animation: fadeIn 0.15s ease-out forwards;
  }
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
</style>
