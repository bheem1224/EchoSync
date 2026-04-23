<script>
  // ─── AudioPlayer.svelte ────────────────────────────────────────────────────
  // Pure view component for the global audio singleton.
  //
  // There is NO <audio> element here. The HTMLAudioElement is owned entirely
  // by the player store (player.js), which also drives isPlaying / currentTime
  // / duration via DOM event listeners. This component only reads store state
  // and calls store actions — it cannot accidentally create a second audio
  // instance regardless of how many times it is mounted.
  // ──────────────────────────────────────────────────────────────────────────
  import { player } from '../stores/player';

  // ── Scrub / seek interaction ───────────────────────────────────────────────
  // While the user is dragging the seek thumb, we freeze the displayed time at
  // the drag position so timeupdate events don't fight the thumb back to the
  // real playback position.
  let scrubbing = false;
  let scrubTime = 0;

  function onScrubStart(e) {
    scrubbing = true;
    scrubTime = parseFloat(e.target.value);
  }

  function onScrubMove(e) {
    scrubTime = parseFloat(e.target.value);
  }

  function onScrubEnd(e) {
    scrubbing = false;
    player.seek(parseFloat(e.target.value));
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  function formatTime(t) {
    if (!t || isNaN(t)) return '0:00';
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  // The seek thumb value: frozen to scrub position while dragging, otherwise
  // follows the live store position.
  $: sliderTime = scrubbing ? scrubTime : $player.currentTime;
</script>

{#if $player.showPlayer && $player.currentTrack}
  <div class="player-bar">

    <!-- Track identity -->
    <div class="track-info">
      <div class="cover-placeholder">🎵</div>
      <div class="meta">
        <span class="title">{$player.currentTrack.title ?? 'Unknown title'}</span>
        <span class="artist">{$player.currentTrack.artist ?? 'Unknown artist'}</span>
      </div>
    </div>

    <!-- Transport controls: Play/Pause + Stop -->
    <div class="controls">
      <button
        class="ctrl-btn play-pause active:scale-95 transition-all duration-200"
        on:click={() => player.toggle()}
        title={$player.isPlaying ? 'Pause' : 'Play'}
        aria-label={$player.isPlaying ? 'Pause' : 'Play'}
      >
        {#if $player.isPlaying}
          <!-- Pause icon -->
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
          </svg>
        {:else}
          <!-- Play icon -->
          <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
            <path d="M8 5v14l11-7z"/>
          </svg>
        {/if}
      </button>

      <button
        class="ctrl-btn stop active:scale-95 transition-all duration-200"
        on:click={() => player.stop()}
        title="Stop"
        aria-label="Stop"
      >
        <!-- Stop (square) icon -->
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
          <path d="M6 6h12v12H6z"/>
        </svg>
      </button>
    </div>

    <!-- Seek bar -->
    <div class="progress">
      <span class="time">{formatTime(sliderTime)}</span>
      <input
        type="range"
        class="seek-slider"
        min="0"
        max={$player.duration || 100}
        step="0.1"
        value={sliderTime}
        on:mousedown={onScrubStart}
        on:touchstart={onScrubStart}
        on:input={onScrubMove}
        on:change={onScrubEnd}
        aria-label="Seek"
      />
      <span class="time">{formatTime($player.duration)}</span>
    </div>

    <!-- Volume -->
    <div class="volume">
      <span class="vol-icon" aria-hidden="true">🔊</span>
      <input
        type="range"
        class="vol-slider"
        min="0"
        max="1"
        step="0.01"
        value={$player.volume}
        on:input={e => player.setVolume(parseFloat(e.target.value))}
        aria-label="Volume"
      />
    </div>

  </div>
{/if}

<style>
  .player-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 80px;
    background: rgba(10, 10, 14, 0.95);
    backdrop-filter: blur(20px);
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    display: grid;
    grid-template-columns: 250px auto 1fr auto;
    align-items: center;
    padding: 0 24px;
    gap: 24px;
    z-index: 1000;
    box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.5);
  }

  .track-info {
    display: flex;
    align-items: center;
    gap: 12px;
    overflow: hidden;
  }

  .cover-placeholder {
      width: 48px;
      height: 48px;
      background: rgba(255,255,255,0.1);
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      flex-shrink: 0;
  }

  .meta {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 0;
  }

  .title {
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 14px;
    color: #fff;
  }

  .artist {
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .controls {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
  }

  /* Play/Pause — larger, filled circle (primary colour) */
  .ctrl-btn.play-pause {
      width: 40px;
      height: 40px;
  }

  /* Stop — smaller, muted ghost circle */
  .ctrl-btn.stop {
      width: 32px;
      height: 32px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-muted);
  }

  .ctrl-btn.stop:hover {
      background: rgba(255, 255, 255, 0.18);
      color: #fff;
  }

  .ctrl-btn {
      background: var(--color-primary);
      color: #000;
      border: none;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.1s;
      padding: 0;
  }

  .ctrl-btn:hover {
      background: var(--color-primary-hover);
      transform: scale(1.05);
  }

  .ctrl-btn:active {
      transform: scale(0.95);
  }

  .progress {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
      max-width: 600px;
      margin: 0 auto;
  }

  .seek-slider {
      flex: 1;
      height: 4px;
      -webkit-appearance: none;
      background: rgba(255,255,255,0.1);
      border-radius: 2px;
      outline: none;
      cursor: pointer;
  }

  .seek-slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--color-primary);
      cursor: pointer;
      transition: transform 0.1s;
  }

  .seek-slider::-webkit-slider-thumb:hover {
      transform: scale(1.2);
  }

  .time {
      font-size: 12px;
      font-family: monospace;
      color: var(--text-muted);
      min-width: 40px;
      text-align: center;
  }

  .volume {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 120px;
  }

  .vol-icon {
      font-size: 14px;
      color: var(--text-muted);
  }

  .vol-slider {
      flex: 1;
      height: 4px;
      -webkit-appearance: none;
      background: rgba(255,255,255,0.1);
      border-radius: 2px;
      cursor: pointer;
  }

  .vol-slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #fff;
      cursor: pointer;
  }

  @media (max-width: 768px) {
      .player-bar {
          grid-template-columns: 1fr auto;
          grid-template-rows: auto;
          height: 64px;
          padding: 0 16px;
          bottom: 60px; /* Leave space for bottom nav */
          border-radius: 12px 12px 0 0;
          background: rgba(20, 24, 31, 0.98);
      }

      .progress, .volume {
          display: none;
      }

      .controls {
          grid-column: 2;
      }

      .track-info {
          grid-column: 1;
      }
  }
</style>
