import { writable } from 'svelte/store';
import apiClient from '../api/client';

function createHealthStore() {
  const { subscribe, set, update } = writable({
    status: 'unknown',
    services: {},
    lastUpdated: null,
  });

  async function load() {
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
    }
  }

  function poll(interval = 30000) {
    load();
    return setInterval(load, interval);
  }

  return {
    subscribe,
    load,
    poll,
  };
}

export const health = createHealthStore();
