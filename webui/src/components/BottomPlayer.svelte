<script>
  // ─── BottomPlayer.svelte ────────────────────────────────────────────────────
  //
  // Single-ownership audio player.  This component owns the ONE <audio> element
  // for the entire app.
  // ─────────────────────────────────────────────────────────────────────────────

  import { onMount, onDestroy } from 'svelte';
  import { player }   from '../stores/player';
  import { feedback } from '../stores/feedback';

  // ── Audio element reference ───────────────────────────────────────────────
  let audioEl = $state();

  // ── State ────────────────────────────────────────────────────────────────
  let paused = $state(true);
  let currentTime = $state(0);
  let duration = $state(0);
  let localVolume = $state(1.0);

  // ── Live-transcode detection ───────────────────────────────────────────────
  const isLiveStream = $derived(!isFinite(duration) || duration === 0);

  // ── Scrub / seek ─────────────────────────────────────────────────────────
  let scrubbing = $state(false);
  let scrubValue = $state(0);

  function onScrubStart(e) {
    scrubbing = true;
    scrubValue = +e.target.value;
  }
  function onScrubMove(e) {
    scrubValue = +e.target.value;
  }
  function onScrubEnd(e) {
    scrubbing = false;
    if (audioEl) audioEl.currentTime = +e.target.value;
  }

  const displayTime = $derived(scrubbing ? scrubValue : currentTime);

  // ── Store → Audio Sync ────────────────────────────────────────────────────
  let lastLoadedUrl = $state(null);

  $effect(() => {
    if ($player.streamUrl !== lastLoadedUrl && audioEl) {
      const newUrl = $player.streamUrl;
      lastLoadedUrl = newUrl;

      if (newUrl) {
        audioEl.src = newUrl;
        audioEl.load();
        audioEl.play().catch(handlePlaybackError);
      } else {
        audioEl.pause();
        audioEl.src = '';
      }
    }
  });

  $effect(() => {
    if ($player.playCommand && audioEl) {
      const cmd = $player.playCommand;
      player.clearPlayCommand();

      if (cmd === 'play') audioEl.play().catch(handlePlaybackError);
      else if (cmd === 'pause') audioEl.pause();
      else if (cmd === 'stop') { 
        audioEl.pause(); 
        audioEl.src = ''; 
        lastLoadedUrl = null; 
      }
    }
  });

  $effect(() => {
    if ($player.seekTo !== null && $player.seekTo !== undefined && audioEl) {
      const t = $player.seekTo;
      player.clearSeekTarget();
      audioEl.currentTime = t;
    }
  });

  $effect(() => {
    localVolume = $player.volume;
  });

  // ── Audio → Store Reporting ───────────────────────────────────────────────
  function onPlay() { player.update(s => ({ ...s, isPlaying: true })); }
  function onPause() { player.update(s => ({ ...s, isPlaying: false })); }
  function onEnded() { player.update(s => ({ ...s, isPlaying: false, currentTime: 0 })); }
  function onTimeUpdate() { player.update(s => ({ ...s, currentTime })); }
  function onDurationChange() {
    player.update(s => ({ ...s, duration: isFinite(duration) ? duration : 0 }));
  }

  // ── Error handling ─────────────────────────────────────────────────────────
  function handleError(e) {
    const mediaError = e.target?.error;
    let msg = 'Playback failed.';
    if (mediaError) {
      if (mediaError.code === MediaError.MEDIA_ERR_NETWORK) msg = 'Playback failed: network error.';
      else if (mediaError.code === MediaError.MEDIA_ERR_DECODE) msg = 'Playback failed: decode error.';
      else if (mediaError.code === MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED) msg = 'Playback failed: format not supported.';
      else msg = `Playback failed: ${mediaError.message || 'unknown error'}.`;
    }
    feedback.addToast(msg, 'error');
    player.update(s => ({ ...s, isPlaying: false }));
  }

  function handlePlaybackError(err) {
    if (err?.name === 'AbortError') return;
    feedback.addToast(`Playback error: ${err?.message ?? 'unknown error'}`, 'error');
  }

  function onToggle() {
    if (!audioEl) return;
    if (paused) audioEl.play().catch(handlePlaybackError);
    else audioEl.pause();
  }

  onMount(() => {
    localVolume = $player.volume;
    if ($player.streamUrl) {
      lastLoadedUrl = $player.streamUrl;
      audioEl.src = $player.streamUrl;
      audioEl.load();
      audioEl.play().catch(handlePlaybackError);
    }
  });

  onDestroy(() => {
    if (audioEl) {
      audioEl.pause();
      audioEl.src = '';
    }
  });

  function formatTime(t) {
    if (!t || !isFinite(t) || isNaN(t)) return '0:00';
    const total = Math.floor(t);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }
</script>

{#if $player.showPlayer && $player.currentTrack}

  <!--
    The <audio> element is hidden from the layout but fully live in the DOM.
    Svelte's bind: directives make it the single source of truth for playback
    state without requiring any imperative event listeners.
  -->
  <audio
    bind:this={audioEl}
    bind:paused
    bind:currentTime
    bind:duration
    bind:volume={localVolume}
    on:play={onPlay}
    on:pause={onPause}
    on:ended={onEnded}
    on:timeupdate={onTimeUpdate}
    on:durationchange={onDurationChange}
    on:error={handleError}
    preload="metadata"
    class="hidden"
  ></audio>

  <!-- ── Fixed bottom bar ───────────────────────────────────────────────── -->
  <div
    class="w-full h-auto min-h-[5rem] py-2 md:py-0 md:h-20 bg-gray-900 border-t border-gray-800
           flex flex-col md:flex-row items-center px-2 md:px-4 gap-2 md:gap-4 relative z-40"
  >

    <!-- ── Mobile Top: Progress Bar (visible only on small screens) ─────────── -->
    <div class="flex md:hidden w-full items-center gap-2 px-2">
      <span class="text-[10px] text-gray-400 tabular-nums shrink-0">{formatTime(displayTime)}</span>
      <input
        type="range"
        min="0"
        max={isLiveStream ? 100 : duration}
        step="0.1"
        value={displayTime}
        disabled={isLiveStream}
        class="flex-1 h-1 accent-white cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
        on:mousedown={onScrubStart}
        on:touchstart|passive={onScrubStart}
        on:input={onScrubMove}
        on:change={onScrubEnd}
        aria-label="Seek"
      />
      {#if isLiveStream}
        <span class="shrink-0 text-[8px] font-semibold px-1 rounded bg-orange-600 text-white">LIVE</span>
      {:else}
        <span class="text-[10px] text-gray-400 tabular-nums shrink-0">{formatTime(duration)}</span>
      {/if}
    </div>

    <div class="flex w-full items-center justify-between md:justify-start gap-2 md:gap-4 flex-1">
      <!-- ── LEFT: Track identity ──────────────────────────── -->
      <div class="flex items-center gap-3 md:w-56 min-w-0 shrink-0 flex-1 md:flex-none">
        <div
          class="w-10 h-10 md:w-12 md:h-12 rounded bg-gray-800 flex items-center justify-center
                 text-lg md:text-xl shrink-0 select-none"
          aria-hidden="true"
        >
          🎵
        </div>

        <div class="min-w-0">
          <p class="text-sm font-semibold text-white truncate leading-tight">
            {$player.currentTrack.title ?? 'Unknown Title'}
          </p>
          <p class="text-xs text-gray-400 truncate mt-0.5">
            {$player.currentTrack.artist ?? 'Unknown Artist'}
          </p>
        </div>
      </div>

      <!-- ── CENTER: Transport controls + Desktop progress bar ────────────── -->
      <div class="flex flex-col items-center md:flex-1 min-w-0 gap-1.5 shrink-0">

        <!-- Transport row -->
        <div class="flex items-center gap-3 md:gap-5">

          <!-- Previous -->
          <button
            class="text-gray-500 hover:text-white transition-colors active:scale-95"
            title="Previous"
            aria-label="Previous track"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M6 6h2v12H6zm3.5 6 8.5 6V6z"/>
            </svg>
          </button>

          <!-- Play / Pause -->
          <button
            class="w-9 h-9 md:w-10 md:h-10 rounded-full bg-white text-gray-900 flex items-center justify-center
                   hover:scale-105 active:scale-95 transition-transform shadow-md"
            on:click={onToggle}
            aria-label={paused ? 'Play' : 'Pause'}
            title={paused ? 'Play' : 'Pause'}
          >
            {#if paused}
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M8 5v14l11-7z"/>
              </svg>
            {:else}
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
              </svg>
            {/if}
          </button>

          <!-- Next -->
          <button
            class="text-gray-500 hover:text-white transition-colors active:scale-95"
            title="Next"
            aria-label="Next track"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M6 18l8.5-6L6 6v12zM16 6h2v12h-2z"/>
            </svg>
          </button>

        </div>

        <!-- Desktop Progress row (hidden on small screens) -->
        <div class="hidden md:flex items-center gap-2 w-full max-w-lg">
          <span class="text-xs text-gray-400 tabular-nums w-10 text-right shrink-0">
            {formatTime(displayTime)}
          </span>
          <input
            type="range"
            min="0"
            max={isLiveStream ? 100 : duration}
            step="0.1"
            value={displayTime}
            disabled={isLiveStream}
            class="flex-1 h-1 accent-white cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
            on:mousedown={onScrubStart}
            on:touchstart|passive={onScrubStart}
            on:input={onScrubMove}
            on:change={onScrubEnd}
            aria-label="Seek"
          />
          {#if isLiveStream}
            <span class="shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-orange-600 text-white tracking-wide">LIVE</span>
          {:else}
            <span class="text-xs text-gray-400 tabular-nums w-10 shrink-0">
              {formatTime(duration)}
            </span>
          {/if}
        </div>
      </div>

      <!-- ── RIGHT: Volume control (hidden on mobile, shifted left on desktop) ── -->
      <div class="hidden md:flex items-center gap-2 w-28 lg:w-32 shrink-0 mr-4 lg:mr-8">
        <svg class="w-4 h-4 text-gray-400 shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
        </svg>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          bind:value={localVolume}
          on:input={e => player.setVolume(+e.target.value)}
          class="flex-1 h-1 accent-white cursor-pointer"
          aria-label="Volume"
        />
      </div>
    </div>
  </div>
{/if}
