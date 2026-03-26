import { writable } from 'svelte/store';
import apiClient from '../api/client';

// Terminal statuses that should be evicted from the active list once they are
// older than this threshold.  A short grace window lets the UI flash the final
// state before the row disappears, rather than vanishing mid-render.
const STALE_TERMINAL_MS = 5000;

function isActiveJob(job) {
  const isTerminal = job.status === 'completed' || job.status === 'failed';
  if (!isTerminal) return true;
  const finishedAt = job.updated_at ? new Date(job.updated_at).getTime() : 0;
  return Date.now() - finishedAt < STALE_TERMINAL_MS;
}

function createJobsStore() {
  const { subscribe, set, update } = writable({
    active: [],
    history: [],
  });

  async function load() {
    try {
      const [active, history] = await Promise.all([
        apiClient.get('/jobs/active'),
        apiClient.get('/jobs'),
      ]);

      // Defensive guards for API shape consistency
      const activeJobs = Array.isArray(active.data) ? active.data :
                        Array.isArray(active.data?.jobs) ? active.data.jobs : [];
      const historyJobs = Array.isArray(history.data) ? history.data :
                         Array.isArray(history.data?.jobs) ? history.data.jobs : [];

      // Drop completed/failed jobs that finished more than STALE_TERMINAL_MS ago
      // so stale entries never stay frozen in the active list.
      set({ active: activeJobs.filter(isActiveJob), history: historyJobs });
    } catch (error) {
      console.error('Failed to load jobs:', error);
      // Reset to empty arrays on error to prevent undefined access
      set({ active: [], history: [] });
    }
  }

  function poll(interval = 3000) {
    load();
    return setInterval(load, interval);
  }

  return {
    subscribe,
    load,
    poll,
  };
}

export const jobs = createJobsStore();
