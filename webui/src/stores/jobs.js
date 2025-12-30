import { writable } from 'svelte/store';
import apiClient from '../api/client';

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
      
      set({ active: activeJobs, history: historyJobs });
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
