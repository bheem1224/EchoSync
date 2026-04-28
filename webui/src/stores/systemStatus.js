import { writable } from 'svelte/store';
import apiClient from '../api/client';

function createSystemStatusStore() {
  const { subscribe, set, update } = writable({
    status: 'online',
    restart_pending: false,
    platform: null,
    python_version: null,
    lastUpdated: null,
  });

  let pollInterval = null;

  async function load() {
    try {
      const response = await apiClient.get('/status');
      set({
        ...response.data,
        lastUpdated: new Date(),
      });
    } catch (error) {
      console.error('Failed to load system status:', error);
      update(state => ({ ...state, status: 'offline' }));
    }
  }

  function startPolling(interval = 5000) {
    if (pollInterval) return;
    load();
    pollInterval = setInterval(load, interval);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  return {
    subscribe,
    load,
    startPolling,
    stopPolling,
  };
}

export const systemStatus = createSystemStatusStore();
