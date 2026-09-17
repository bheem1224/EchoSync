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

  let eventSource = null;
  // Require 4 consecutive failures before showing the offline banner.
  let consecutiveFailures = 0;
  const FAILURES_BEFORE_OFFLINE = 4;

  async function load() {
    try {
      const response = await apiClient.get('/system/health');
      consecutiveFailures = 0;
      set({
        ...response.data,
        lastUpdated: new Date(),
      });
    } catch {
      consecutiveFailures += 1;
      if (consecutiveFailures >= FAILURES_BEFORE_OFFLINE) {
        update(state => ({ ...state, status: 'offline' }));
      }
      // Below threshold: stay silent — don't set offline yet
    }
  }

  function startPolling() {
    if (eventSource) return;
    // Initial fetch for instantaneous render
    load();

    try {
      eventSource = new EventSource('/api/v1/system/tasks/stream');
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          consecutiveFailures = 0;
          const system = data.system || {};
          const health = data.health || {};
          set({
            status: system.status || health.status || 'online',
            restart_pending: Boolean(system.restart_pending),
            platform: system.platform || null,
            python_version: system.python_version || null,
            uptime: system.uptime,
            lastUpdated: new Date(),
          });
        } catch (err) {
          console.error('Failed to parse system status SSE event:', err);
        }
      };

      eventSource.onerror = () => {
        consecutiveFailures += 1;
        if (consecutiveFailures >= FAILURES_BEFORE_OFFLINE) {
          update(state => ({ ...state, status: 'offline' }));
        }
      };
    } catch (err) {
      console.error('Failed to establish EventSource connection:', err);
    }
  }

  function stopPolling() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    consecutiveFailures = 0;
  }

  return {
    subscribe,
    load,
    startPolling,
    stopPolling,
  };
}

export const systemStatus = createSystemStatusStore();
