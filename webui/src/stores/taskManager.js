import { writable } from 'svelte/store';
import apiClient from '../api/client';
import { API_BASE_URL } from '../api/client';

const initialQueueState = {
  running_jobs: [],
  pending_jobs: [],
  blocked_jobs: [],
  stats: {
    total: 0,
    running: 0,
    pending: 0,
    blocked: 0
  },
  cancellingJobs: new Set()
};

function createTaskManagerStore() {
  const { subscribe, set, update } = writable(initialQueueState);
  let eventSource = null;
  let reconnectTimer = null;
  let reconnectDelay = 2000; // start at 2s, cap at 30s

  function connect(streamUrl = `${API_BASE_URL}/system/jobs/stream`) {
    disconnect();

    try {
      eventSource = new EventSource(streamUrl, { withCredentials: true });

      // Plain `data:` frames (no named event type)
      eventSource.onmessage = (event) => {
        reconnectDelay = 2000; // reset backoff on successful message
        try {
          const payload = JSON.parse(event.data);
          update((state) => ({
            ...state,
            running_jobs: payload.running_jobs || [],
            pending_jobs: payload.pending_jobs || [],
            blocked_jobs: payload.blocked_jobs || [],
            stats: payload.stats || { total: 0, running: 0, pending: 0, blocked: 0 }
          }));
        } catch (err) {
          console.error('Error parsing queue stream SSE event:', err);
        }
      };

      // Named event type (legacy compatibility)
      eventSource.addEventListener('queue_update', (event) => {
        eventSource.onmessage(event);
      });

      eventSource.onerror = () => {
        disconnect();
        // Exponential backoff reconnect
        reconnectTimer = setTimeout(() => {
          reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
          connect(streamUrl);
        }, reconnectDelay);
      };
    } catch (err) {
      console.error('Failed to connect TaskManager SSE:', err);
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  }

  async function cancelJob(jobName) {
    update((state) => {
      const cancelling = new Set(state.cancellingJobs);
      cancelling.add(jobName);
      return { ...state, cancellingJobs: cancelling };
    });

    try {
      const response = await apiClient.post(`/system/jobs/${jobName}/cancel`);

      if (response.status !== 200) {
        throw new Error(`Failed to cancel job: ${(response.statusText || 'Error')}`);
      }
    } catch (err) {
      console.error(`Error cancelling job ${jobName}:`, err);
    } finally {
      setTimeout(() => {
        update((state) => {
          const cancelling = new Set(state.cancellingJobs);
          cancelling.delete(jobName);
          return { ...state, cancellingJobs: cancelling };
        });
      }, 1500);
    }
  }

  return {
    subscribe,
    connect,
    disconnect,
    cancelJob,
    reset: () => set(initialQueueState)
  };
}

export const taskManager = createTaskManagerStore();

