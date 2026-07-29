import { writable } from 'svelte/store';

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

  function connect(streamUrl = '/api/v1/system/queue/stream') {
    disconnect();

    try {
      eventSource = new EventSource(streamUrl);

      eventSource.onmessage = (event) => {
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

      eventSource.onerror = (error) => {
        console.error('TaskManager SSE connection error:', error);
        if (eventSource?.readyState === EventSource.CLOSED) {
          disconnect();
        }
      };
    } catch (err) {
      console.error('Failed to connect TaskManager SSE:', err);
    }
  }

  function disconnect() {
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
      const response = await fetch('/api/v1/system/queue/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_name: jobName })
      });

      if (!response.ok) {
        throw new Error(`Failed to cancel job: ${response.statusText}`);
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
