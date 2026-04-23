<script>
  // ─── BottomPlayer.svelte ────────────────────────────────────────────────────
  //
  // Single-ownership audio player.  This component owns the ONE <audio> element
  // for the entire app.  Svelte's bind: directives keep local variables in sync
  // with the element's live DOM properties; all other components interact with
  // audio playback exclusively through the player store.
  //
  // Store → Component (command bus):
  //   $player.streamUrl   — load a new track and autoplay
  //   $player.playCommand — one-shot 'play' | 'pause' | 'stop'
  //   $player.seekTo      — one-shot absolute seek position (seconds)
  //   $player.volume      — desired volume level (0–1)
  //
  // Component → Store (state reporting):
  //   on:play / on:pause  → player.update({ isPlaying })
  //   on:timeupdate       → player.update({ currentTime })
  //   on:durationchange   → player.update({ duration })
  //
  // Live-transcode streams (DSF/DFF/APE/WMA via FFmpeg) have no Content-Length,
  // so `duration` resolves to Infinity or NaN.  The isLiveStream flag disables
  // the seek bar and replaces the total-time label with a 'LIVE' badge.
  // ─────────────────────────────────────────────────────────────────────────────

  import { onMount, onDestroy } from 'svelte';
  import { player }   from '../stores/player';
  import { feedback } from '../stores/feedback';

  // ── Audio element reference (populated by bind:this) ──────────────────────
  let audioEl;

  // ── Two-way Svelte audio bindings ─────────────────────────────────────────
  // Svelte keeps these variables in sync with the corresponding HTMLAudioElement
  // DOM properties.  Writing to them also propagates back to the element.
  let paused       = true;
  let currentTime  = 0;
  let duration     = 0;
  let localVolume  = 1.0;   // named to avoid shadowing the CSS `volume` property

  // ── Live-transcode detection ───────────────────────────────────────────────
  // FFmpeg live-transcode responses carry no Content-Length, so the browser
  // cannot determine the total duration.  It exposes this as Infinity or NaN.
  $: isLiveStream = !isFinite(duration) || duration === 0;

  // ── Scrub / seek: freeze thumb while the user is dragging ────────────────
  let scrubbing  = false;
  let scrubValue = 0;

  function onScrubStart(e) {
    scrubbing  = true;
    scrubValue = +e.target.value;
  }
  function onScrubMove(e) {
    scrubValue = +e.target.value;
  }
  function onScrubEnd(e) {
    scrubbing = false;
    if (audioEl) audioEl.currentTime = +e.target.value;
  }

  // The value shown in the time label and driving the range thumb:
  // frozen to scrubValue while the user is dragging so timeupdate events
  // don't fight the thumb back to the real playback position.
  $: displayTime = scrubbing ? scrubValue : currentTime;

  // ── Store → Audio: load + autoplay whenever the URL changes ──────────────
  // `lastLoadedUrl` prevents reloading when other store fields update.
  let lastLoadedUrl = null;

  $: if ($player.streamUrl !== lastLoadedUrl && audioEl) {
    const newUrl    = $player.streamUrl;
    lastLoadedUrl   = newUrl;

    if (newUrl) {
      audioEl.src = newUrl;
      audioEl.load();
      audioEl.play().catch(handlePlaybackError);
    } else {
      // streamUrl was cleared (stop() was called)
      audioEl.pause();
      audioEl.src = '';
    }
  }

  // ── Store → Audio: one-shot play / pause / stop commands ─────────────────
  // External callers (keyboard shortcuts, other components) use player.pause()
  // / player.resume() which set `playCommand`.  BottomPlayer consumes and
  // clears the command so it fires exactly once.
  $: if ($player.playCommand && audioEl) {
    const cmd = $player.playCommand;
    player.clearPlayCommand();                                // consume immediately

    if      (cmd === 'play')  audioEl.play().catch(handlePlaybackError);
    else if (cmd === 'pause') audioEl.pause();
    else if (cmd === 'stop')  { audioEl.pause(); audioEl.src = ''; lastLoadedUrl = null; }
  }

  // ── Store → Audio: one-shot seek ─────────────────────────────────────────
  $: if ($player.seekTo !== null && $player.seekTo !== undefined && audioEl) {
    const t = $player.seekTo;
    player.clearSeekTarget();                                 // consume immediately
    audioEl.currentTime = t;
  }

  // ── Store → Audio: volume ─────────────────────────────────────────────────
  // Reactive assignment keeps localVolume (and therefore bind:volume on the
  // <audio> element) in sync when an external caller changes store volume.
  $: localVolume = $player.volume;

  // ── Audio → Store: report live playback state back to the store ──────────
  // Other components (e.g. a mini player, keyboard handler) read isPlaying,
  // currentTime, and duration from the store.
  function onPlay()           { player.update(s => ({ ...s, isPlaying: true  })); }
  function onPause()          { player.update(s => ({ ...s, isPlaying: false })); }
  function onEnded()          { player.update(s => ({ ...s, isPlaying: false, currentTime: 0 })); }
  function onTimeUpdate()     { player.update(s => ({ ...s, currentTime })); }
  function onDurationChange() {
    player.update(s => ({ ...s, duration: isFinite(duration) ? duration : 0 }));
  }

  // ── Error handling ─────────────────────────────────────────────────────────
  function handleError(e) {
    const mediaError = e.target?.error;
    let msg = 'Playback failed.';
    if (mediaError) {
      if      (mediaError.code === MediaError.MEDIA_ERR_NETWORK)          msg = 'Playback failed: network error.';
      else if (mediaError.code === MediaError.MEDIA_ERR_DECODE)           msg = 'Playback failed: decode error.';
      else if (mediaError.code === MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED) msg = 'Playback failed: format not supported.';
      else    msg = `Playback failed: ${mediaError.message || 'unknown error'}.`;
    }
    feedback.addToast(msg, 'error');
    player.update(s => ({ ...s, isPlaying: false }));
  }

  // AbortError is benign: the browser fires it when play() is interrupted by
  // a src change (e.g. the user clicks a new track before the first one loads).
  function handlePlaybackError(err) {
    if (err?.name === 'AbortError') return;
    feedback.addToast(`Playback error: ${err?.message ?? 'unknown error'}`, 'error');
  }

  // ── Play / Pause button ────────────────────────────────────────────────────
  // Drives the audio element directly; bind:paused keeps the icon in sync.
  function onToggle() {
    if (!audioEl) return;
    if (paused) audioEl.play().catch(handlePlaybackError);
    else        audioEl.pause();
  }

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  onMount(() => {
    // Inherit current volume from store immediately so there is no blast on first play.
    localVolume = $player.volume;

    // Handle the case where the store already holds a track URL when this
    // component mounts (e.g. during SvelteKit hot-module replacement).
    if ($player.streamUrl) {
      lastLoadedUrl   = $player.streamUrl;
      audioEl.src     = $player.streamUrl;
      audioEl.load();
      audioEl.play().catch(handlePlaybackError);
    }
  });

  onDestroy(() => {
    // Release the audio resource when the component is torn down.
    if (audioEl) {
      audioEl.pause();
      audioEl.src = '';
    }
  });

  // ── Helpers ────────────────────────────────────────────────────────────────
  function formatTime(t) {
    if (!t || !isFinite(t) || isNaN(t)) return '0:00';
    const total = Math.floor(t);
    const h     = Math.floor(total / 3600);
    const m     = Math.floor((total % 3600) / 60);
    const s     = total % 60;
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
    class="fixed bottom-0 left-0 right-0 h-20 bg-gray-900 border-t border-gray-800
           flex items-center px-4 gap-4 z-50"
  >

    <!-- ── LEFT: Track identity (fixed 224 px) ──────────────────────────── -->
    <div class="flex items-center gap-3 w-56 min-w-0 shrink-0">
      <div
        class="w-12 h-12 rounded bg-gray-800 flex items-center justify-center
               text-xl shrink-0 select-none"
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

    <!-- ── CENTER: Transport controls + progress bar (flex-1) ────────────── -->
    <div class="flex flex-col items-center flex-1 min-w-0 gap-1.5">

      <!-- Transport row -->
      <div class="flex items-center gap-5">

        <!-- Previous (stub — future queue integration) -->
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
          class="w-9 h-9 rounded-full bg-white text-gray-900 flex items-center justify-center
                 hover:scale-105 active:scale-95 transition-transform"
          on:click={onToggle}
          aria-label={paused ? 'Play' : 'Pause'}
          title={paused ? 'Play' : 'Pause'}
        >
          {#if paused}
            <!-- Play icon -->
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M8 5v14l11-7z"/>
            </svg>
          {:else}
            <!-- Pause icon -->
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
            </svg>
          {/if}
        </button>

        <!-- Next (stub — future queue integration) -->
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

      <!-- Progress row -->
      <div class="flex items-center gap-2 w-full max-w-lg">

        <!-- Elapsed time -->
        <span class="text-xs text-gray-400 tabular-nums w-10 text-right shrink-0">
          {formatTime(displayTime)}
        </span>

        <!--
          Seek slider.
          Disabled (greyed, non-interactive) for live-transcode streams because
          the browser has no total-duration information to seek against.
          The `value` attribute (not bind:value) is used intentionally: we drive
          the thumb position ourselves (scrub-aware), which prevents the browser
          from snapping the thumb back during timeupdate while dragging.
        -->
        <input
          type="range"
          min="0"
          max={isLiveStream ? 100 : duration}
          step="0.1"
          value={displayTime}
          disabled={isLiveStream}
          class="flex-1 h-1 accent-white cursor-pointer
                 disabled:cursor-not-allowed disabled:opacity-40"
          on:mousedown={onScrubStart}
          on:touchstart|passive={onScrubStart}
          on:input={onScrubMove}
          on:change={onScrubEnd}
          aria-label="Seek"
        />

        <!--
          Show a 'LIVE' badge when duration is unknown (live transcode).
          Show elapsed/total times for normal seekable files.
        -->
        {#if isLiveStream}
          <span
            class="shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded
                   bg-orange-600 text-white tracking-wide"
            title="Live transcode — seeking unavailable"
          >
            LIVE
          </span>
        {:else}
          <span class="text-xs text-gray-400 tabular-nums w-10 shrink-0">
            {formatTime(duration)}
          </span>
        {/if}

      </div>
    </div>

    <!-- ── RIGHT: Volume control (fixed 128 px) ─────────────────────────── -->
    <div class="flex items-center gap-2 w-32 shrink-0">
      <svg
        class="w-4 h-4 text-gray-400 shrink-0"
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
      </svg>

      <!--
        bind:value keeps the slider thumb in sync with `localVolume`.
        on:input calls player.setVolume() to persist the preference in the store
        so external volume-change callers (e.g. keyboard shortcuts) stay in sync.
      -->
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
{/if}
