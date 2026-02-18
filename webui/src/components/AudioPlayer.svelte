<script>
  import { onMount } from 'svelte';
  import { player } from '../stores/player';

  let audio;
  let duration = 0;
  let currentTime = 0;

  // React to store changes for Play/Pause
  $: if (audio) {
    if ($player.isPlaying && audio.paused) {
      audio.play().catch(e => {
        console.error("Playback error:", e);
        player.pause(); // Revert state if play fails
      });
    } else if (!$player.isPlaying && !audio.paused) {
      audio.pause();
    }

    // Volume control
    if (Math.abs(audio.volume - $player.volume) > 0.01) {
        audio.volume = $player.volume;
    }
  }

  // React to seek request from store (if different from current)
  // But wait, bind:currentTime handles reading. Writing?
  // If I drag slider, it updates audio.currentTime.
  // If store updates (e.g. skip), I need to update audio.
  // But store.currentTime is updated by audio timeupdate.
  // Let's use bind:currentTime for the read-loop, and seek method for write.

  function handleTimeUpdate() {
    // Only update store if difference is significant to avoid churn?
    // Actually Svelte stores are cheap.
    player.setCurrentTime(currentTime);
  }

  function handleDurationChange() {
    player.setDuration(duration);
  }

  function handleEnded() {
    player.pause();
  }

  function handlePlay() {
      if (!$player.isPlaying) player.play();
  }

  function handlePause() {
      if ($player.isPlaying) player.pause();
  }

  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  function handleSeek(e) {
      const time = parseFloat(e.target.value);
      currentTime = time; // Updates audio immediately via binding? No, bind:currentTime is two-way.
      // Actually, if I bind value={currentTime}, input updates variable.
      // Variable updates audio because of bind:currentTime={currentTime} on audio.
  }

  function handleVolume(e) {
      const vol = parseFloat(e.target.value);
      player.setVolume(vol);
  }

  // Reactive src
  $: src = $player.currentTrack ? player.getStreamUrl($player.currentTrack.id) : '';

  // Auto-play when track changes (src updates)
  $: if (src && audio && $player.isPlaying) {
      // Small timeout to allow audio element to load new src
      setTimeout(() => {
          audio.play().catch(console.error);
      }, 50);
  }
</script>

{#if $player.showPlayer && $player.currentTrack}
  <div class="player-bar">
    <audio
      bind:this={audio}
      bind:currentTime={currentTime}
      bind:duration={duration}
      on:timeupdate={handleTimeUpdate}
      on:durationchange={handleDurationChange}
      on:ended={handleEnded}
      on:play={handlePlay}
      on:pause={handlePause}
      {src}
      preload="auto"
    ></audio>

    <div class="track-info">
        <div class="cover-placeholder">🎵</div>
        <div class="meta">
            <span class="title">{$player.currentTrack.title}</span>
            <span class="artist">{$player.currentTrack.artist}</span>
        </div>
    </div>

    <div class="controls">
        <button class="ctrl-btn" on:click={() => player.toggle()} title={$player.isPlaying ? "Pause" : "Play"}>
            {#if $player.isPlaying}
                <!-- Pause Icon -->
                <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            {:else}
                <!-- Play Icon -->
                <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
            {/if}
        </button>
    </div>

    <div class="progress">
        <span class="time">{formatTime(currentTime)}</span>
        <input
            type="range"
            min="0"
            max={duration || 100}
            value={currentTime}
            on:input={handleSeek}
            class="seek-slider"
        />
        <span class="time">{formatTime(duration)}</span>
    </div>

    <div class="volume">
        <span class="vol-icon">🔊</span>
        <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={$player.volume}
            on:input={handleVolume}
            class="vol-slider"
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
