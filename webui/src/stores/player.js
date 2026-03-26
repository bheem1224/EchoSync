import { writable, get } from 'svelte/store';

// ─────────────────────────────────────────────────────────────────────────────
// Command-bus player store
//
// The HTMLAudioElement is owned entirely by BottomPlayer.svelte, which binds
// to it with Svelte's bind: directives.  This store acts as a command bus:
//
//   Callers → store.playTrack / pause / resume / seek / setVolume / stop
//   Store   → BottomPlayer via reactive fields: streamUrl, playCommand, seekTo
//   BottomPlayer → store via store.update() to sync currentTime/duration/isPlaying
//
// This design keeps a single audio element alive in the DOM and prevents the
// double-playback bug that occurs when both a store singleton and a component
// element try to play the same URL simultaneously.
// ─────────────────────────────────────────────────────────────────────────────

function createPlayerStore() {
  const _store = writable({
    isPlaying:    false,
    currentTrack: null,
    streamUrl:    null,   // BottomPlayer watches this to load/play new tracks
    playCommand:  null,   // One-shot command: 'play' | 'pause' | 'stop' | null
    seekTo:       null,   // One-shot seek target in seconds; null when idle
    volume:       1.0,
    currentTime:  0,
    duration:     0,
    showPlayer:   false,
  });

  const { subscribe, set, update } = _store;

  // ── Core API ───────────────────────────────────────────────────────────────

  /**
   * Load and immediately play a track.
   * Sets streamUrl in state; BottomPlayer reacts and drives the <audio> element.
   * @param {string}  url           Stream URL
   * @param {object}  trackMetadata Arbitrary track info (id, title, artist …)
   */
  function playTrack(url, trackMetadata) {
    update(s => ({
      ...s,
      streamUrl:    url,
      currentTrack: trackMetadata,
      playCommand:  null,   // BottomPlayer auto-plays on URL change
      seekTo:       null,
      isPlaying:    false,  // BottomPlayer sets true once play() resolves
      currentTime:  0,
      duration:     0,
      showPlayer:   true,
    }));
  }

  /**
   * Pause the current track.
   * Issues a 'pause' command consumed by BottomPlayer.
   */
  function pause() {
    update(s => ({ ...s, playCommand: 'pause', isPlaying: false }));
  }

  /**
   * Resume playback from the current position.
   * Issues a 'play' command consumed by BottomPlayer.
   */
  function resume() {
    update(s => ({ ...s, playCommand: 'play', isPlaying: true }));
  }

  /**
   * Stop playback and clear the player UI entirely.
   * Issues a 'stop' command and resets all state.
   */
  function stop() {
    const { volume } = get(_store); // preserve the user's volume preference
    set({
      isPlaying:    false,
      currentTrack: null,
      streamUrl:    null,
      playCommand:  'stop',
      seekTo:       null,
      volume,
      currentTime:  0,
      duration:     0,
      showPlayer:   false,
    });
  }

  /**
   * Seek to an absolute time in seconds.
   * Sets seekTo in state; BottomPlayer reacts and clears it via clearSeekTarget().
   */
  function seek(time) {
    if (isFinite(time)) {
      update(s => ({ ...s, seekTo: time, currentTime: time }));
    }
  }

  /** Clear the one-shot seek target after BottomPlayer has consumed it. */
  function clearSeekTarget() {
    update(s => ({ ...s, seekTo: null }));
  }

  /** Clear the one-shot play command after BottomPlayer has consumed it. */
  function clearPlayCommand() {
    update(s => ({ ...s, playCommand: null }));
  }

  /** Set playback volume (clamped 0 – 1). */
  function setVolume(level) {
    const volume = Math.max(0, Math.min(1, level));
    update(s => ({ ...s, volume }));
  }

  // ── Backward-compat helpers (used by library/+page.svelte) ────────────────

  /**
   * Legacy `player.play(track)` call site support.
   * When called with a track object, delegates to playTrack().
   * When called with no argument, resumes current playback.
   */
  function play(track) {
    if (!track) { resume(); return; }
    playTrack(`/api/library/stream/${track.id}`, track);
  }

  function toggle() {
    if (get(_store).isPlaying) pause(); else resume();
  }

  function getStreamUrl(trackId) {
    return `/api/library/stream/${trackId}`;
  }

  return {
    subscribe,
    update,          // exposed so BottomPlayer can sync currentTime/duration/isPlaying back
    // Primary API
    playTrack,
    pause,
    resume,
    stop,
    seek,
    clearSeekTarget,
    clearPlayCommand,
    setVolume,
    // Backward-compat aliases
    play,
    toggle,
    getStreamUrl,
  };
}

export const player = createPlayerStore();
