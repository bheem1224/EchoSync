import { writable } from 'svelte/store';
import apiClient from '../api/client';

function createHealthStore() {
  const { subscribe, set, update } = writable({
    status: 'unknown',
    services: {},
    lastUpdated: null,
  });

  let loading = false;
  let pollInterval = null;

  async function load() {
    if (loading) return;
    loading = true;
    try {
      const response = await apiClient.get('/health');
      set({
        status: response.data.status,
        services: response.data.results || {},
        lastUpdated: new Date(),
      });
    } catch (error) {
      console.error('Failed to load health status:', error);
      set({
        status: 'error',
        services: {},
        lastUpdated: new Date(),
      });
    } finally {
      loading = false;
    }
  }

  function poll(interval = 30000) {
    if (pollInterval) return pollInterval;

    load();
    pollInterval = setInterval(load, interval);
    return pollInterval;
  }

  function stop() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  return {
    subscribe,
    load,
    poll,
    stop,
  };
}

export const health = createHealthStore();
