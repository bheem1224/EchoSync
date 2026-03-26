import { writable, get } from 'svelte/store';

// ─────────────────────────────────────────────────────────────────────────────
// Module-level Audio singleton
//
// Keeping the actual HTMLAudioElement at module scope (rather than only inside
// the store state) lets event-listener callbacks guard against stale closures
// with a simple identity check: `if (audio !== _currentAudio) return;`
// This prevents a torn-down audio element from writing back into the store
// after a new track has already been loaded.
// ─────────────────────────────────────────────────────────────────────────────
let _currentAudio = null;

/**
 * Release all resources held by an HTMLAudioElement.
 * Must be called before creating a new Audio instance to prevent overlap.
 */
function _teardown(audio) {
  if (!audio) return;
  try {
    audio.pause();
    audio.src = ''; // signals the browser to drop buffered network data
  } catch (_) {
    // Ignore any DOM errors during cleanup
  }
}

function createPlayerStore() {
  const _store = writable({
    isPlaying:    false,
    currentTrack: null,
    audioContext: null,   // The live HTMLAudioElement; null when stopped
    volume:       1.0,
    currentTime:  0,
    duration:     0,
    showPlayer:   false,
  });

  const { subscribe, set, update } = _store;

  // ── Core API ───────────────────────────────────────────────────────────────

  /**
   * Load and immediately play a track.
   * @param {string}  url           Full URL passed to new Audio()
   * @param {object}  trackMetadata Arbitrary track info (id, title, artist …)
   */
  function playTrack(url, trackMetadata) {
    if (typeof Audio === 'undefined') return; // SSR guard

    // ── CRITICAL: always silence and discard the previous element first ───
    _teardown(_currentAudio);
    _currentAudio = null;

    const audio = new Audio(url);
    _currentAudio = audio;

    // Propagate browser events back into the store.
    // Each handler uses the identity guard to silently ignore callbacks that
    // arrive after the audio element has already been superseded.
    audio.addEventListener('timeupdate', () => {
      if (audio !== _currentAudio) return;
      update(s => ({ ...s, currentTime: audio.currentTime }));
    });
    audio.addEventListener('durationchange', () => {
      if (audio !== _currentAudio) return;
      update(s => ({ ...s, duration: isFinite(audio.duration) ? audio.duration : 0 }));
    });
    audio.addEventListener('ended', () => {
      if (audio !== _currentAudio) return;
      update(s => ({ ...s, isPlaying: false, currentTime: 0 }));
    });
    audio.addEventListener('error', () => {
      if (audio !== _currentAudio) return;
      console.error('[player] HTMLAudioElement error for:', url);
      update(s => ({ ...s, isPlaying: false }));
    });

    // Inherit the current volume so the new track doesn't blast or go silent.
    audio.volume = get(_store).volume;

    // Push new track into the store before calling play() so the UI
    // can render the track name immediately.
    update(s => ({
      ...s,
      audioContext: audio,
      currentTrack: trackMetadata,
      isPlaying:    false,   // becomes true once play() resolves
      currentTime:  0,
      duration:     0,
      showPlayer:   true,
    }));

    audio.play()
      .then(()  => update(s => ({ ...s, isPlaying: true })))
      .catch(err => {
        console.error('[player] play() rejected:', err);
        update(s => ({ ...s, isPlaying: false }));
      });
  }

  /** Pause the current track (retains position and track info). */
  function pause() {
    const { audioContext } = get(_store);
    if (audioContext) {
      audioContext.pause();
      update(s => ({ ...s, isPlaying: false }));
    }
  }

  /** Resume playback from the current position. */
  function resume() {
    const { audioContext } = get(_store);
    if (audioContext) {
      audioContext.play()
        .then(()  => update(s => ({ ...s, isPlaying: true })))
        .catch(err => console.error('[player] resume() rejected:', err));
    }
  }

  /** Stop playback and clear the player UI entirely. */
  function stop() {
    const { volume } = get(_store); // preserve user's volume preference
    _teardown(_currentAudio);
    _currentAudio = null;
    set({
      isPlaying:    false,
      currentTrack: null,
      audioContext: null,
      volume,
      currentTime:  0,
      duration:     0,
      showPlayer:   false,
    });
  }

  /** Seek to an absolute time in seconds. */
  function seek(time) {
    const { audioContext } = get(_store);
    if (audioContext && isFinite(time)) {
      audioContext.currentTime = time;
      update(s => ({ ...s, currentTime: time }));
    }
  }

  /** Set playback volume (clamped 0 – 1). */
  function setVolume(level) {
    const volume = Math.max(0, Math.min(1, level));
    const { audioContext } = get(_store);
    if (audioContext) audioContext.volume = volume;
    update(s => ({ ...s, volume }));
  }

  // ── Backward-compat helpers (used by library/+page.svelte and AudioPlayer) ─

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
    // Primary API
    playTrack,
    pause,
    resume,
    stop,
    seek,
    setVolume,
    // Backward-compat aliases
    play,
    toggle,
    getStreamUrl,
  };
}

export const player = createPlayerStore();
