import { writable } from 'svelte/store';
import apiClient from '../api/client';

function createPlayerStore() {
  const { subscribe, set, update } = writable({
    currentTrack: null,
    isPlaying: false,
    volume: 1.0,
    duration: 0,
    currentTime: 0,
    showPlayer: false, // UI visibility
    loading: false
  });

  return {
    subscribe,
    play: async (track) => {
      // If we pass a track, update the current track
      if (track) {
        update(state => ({
          ...state,
          currentTrack: track,
          isPlaying: true,
          showPlayer: true,
          loading: true,
          duration: 0,
          currentTime: 0
        }));
      } else {
        // Just resume playback
        update(state => ({ ...state, isPlaying: true }));
      }
    },
    pause: () => {
      update(state => ({ ...state, isPlaying: false }));
    },
    toggle: () => {
      update(state => ({ ...state, isPlaying: !state.isPlaying }));
    },
    stop: () => {
      update(state => ({
        ...state,
        currentTrack: null,
        isPlaying: false,
        currentTime: 0,
        duration: 0,
        showPlayer: false
      }));
    },
    setVolume: (level) => {
      // Clamp between 0 and 1
      const volume = Math.max(0, Math.min(1, level));
      update(state => ({ ...state, volume }));
    },
    seek: (time) => {
      update(state => ({ ...state, currentTime: time }));
    },
    setDuration: (duration) => {
      update(state => ({ ...state, duration }));
    },
    setCurrentTime: (time) => {
      update(state => ({ ...state, currentTime: time }));
    },
    setLoading: (loading) => {
      update(state => ({ ...state, loading }));
    },
    // Helper to get stream URL
    getStreamUrl: (trackId) => {
      return `/api/library/stream/${trackId}`;
    }
  };
}

export const player = createPlayerStore();
