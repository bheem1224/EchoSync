import { writable } from 'svelte/store';
import apiClient from '../api/client';

function createMetadataQueueStore() {
  const { subscribe, set, update } = writable({ count: 0, items: [] });

  async function fetchCount() {
    // NOTE: apiClient.baseURL is already "/api" (or "http://host:5000/api" in dev).
    // Use a relative path without the /api prefix to avoid a doubled segment.
    try {
      const resp = await apiClient.get('/metadata/queue');
      const queue = resp.data?.queue || [];
      update(s => ({ ...s, count: queue.length, items: queue }));
    } catch (e) {
      // Graceful degradation: the metadata queue is an optional endpoint.
      // A 404 means the backend hasn't registered it yet – fall back silently.
      if (e?.response?.status === 404) {
        console.warn('[metadataQueue] /api/metadata/queue not found – endpoint may not be active yet. Defaulting to empty queue.');
      } else {
        console.warn('[metadataQueue] Failed to fetch metadata queue:', e?.message ?? e);
      }
      // Keep existing store state (count: 0, items: []) — do NOT re-throw.
    }
  }

  return { subscribe, fetchCount, set };
}

export const metadataQueue = createMetadataQueueStore();
