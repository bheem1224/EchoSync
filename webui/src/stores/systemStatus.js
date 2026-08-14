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
  // Require 4 consecutive failures (20s) before showing the offline banner.
  // This prevents transient lock contentions during intensive database syncs
  // from triggering the offline banner prematurely.
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
