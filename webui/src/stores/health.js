import { writable } from 'svelte/store';
import apiClient from '../api/client';

function createHealthStore() {
  const { subscribe, set, update } = writable({
    status: 'unknown',
    services: {},
    lastUpdated: null,
  });

  let loading = false;
  let eventSource = null;

  async function load() {
    if (loading) return;
    loading = true;
    try {
      const response = await apiClient.get('/system/health');
      set({
        status: response.data.status,
        services: response.data.results || {},
        summary: response.data.summary || { total: 0, operational: 0 },
        lastUpdated: new Date(),
      });
    } catch (error) {
      console.error('Failed to load health status:', error);
      set({
        status: 'error',
        services: {},
        summary: { total: 0, operational: 0 },
        lastUpdated: new Date(),
      });
    } finally {
      loading = false;
    }
  }

  function poll() {
    load();
    if (eventSource) eventSource.close();
    eventSource = new EventSource('/api/v1/system/telemetry/stream', { withCredentials: true });
    eventSource.addEventListener('system_health', (event) => {
      try {
        const payload = JSON.parse(event.data);
        set({
          status: payload.status || 'unknown',
          services: payload.results || {},
          summary: payload.summary || { total: 0, operational: 0 },
          lastUpdated: new Date(),
        });
      } catch (error) {
        console.error('Failed to parse health SSE event:', error);
      }
    });
    return eventSource;
  }

  function stop() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
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
